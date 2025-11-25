"""
本地媒体文件路由
支持不使用 Jellyfin 的用户直接扫描本地文件系统
"""

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_user
from app.core.db import get_db
from app.models.translation_job import TranslationJob
from app.models.user import User
from app.schemas.jobs import JobResponse
from app.services.local_media_scanner import LocalMediaScanner
from app.workers.tasks import asr_then_translate_task, translate_subtitle_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/local-media", tags=["local-media"])


# ============================================================================
# Schemas
# ============================================================================


class ScanDirectoryRequest(BaseModel):
    """扫描目录请求"""

    directory: str = Field(..., description="要扫描的目录路径")
    recursive: bool = Field(True, description="是否递归扫描子目录")
    max_depth: int = Field(5, description="递归最大深度")
    required_langs: list[str] | None = Field(
        None, description="必需的语言代码列表（如 ['zh-CN', 'en']）"
    )

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """验证目录存在且可访问"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        if not path.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return str(path.resolve())


class MediaFileResponse(BaseModel):
    """媒体文件响应"""

    filepath: str = Field(..., description="媒体文件路径")
    filename: str = Field(..., description="文件名")
    size_bytes: int = Field(..., description="文件大小（字节）")
    existing_subtitle_langs: list[str] = Field(default_factory=list, description="已有字幕语言")
    missing_languages: list[str] = Field(default_factory=list, description="缺失的语言")
    subtitle_files: list[str] = Field(default_factory=list, description="字幕文件列表")


class ScanDirectoryResponse(BaseModel):
    """扫描目录响应"""

    directory: str = Field(..., description="扫描的目录")
    media_files: list[MediaFileResponse] = Field(..., description="媒体文件列表")
    total_count: int = Field(..., description="媒体文件总数")
    required_langs: list[str] = Field(..., description="必需的语言列表")


class DirectoryStatsResponse(BaseModel):
    """目录统计响应"""

    directory: str
    total_media_files: int
    total_size_bytes: int
    total_subtitle_files: int
    video_formats: dict[str, int]  # 格式: 数量


class CreateLocalJobRequest(BaseModel):
    """创建本地文件翻译任务请求"""

    filepath: str = Field(..., description="媒体文件路径")
    target_langs: list[str] = Field(..., description="目标语言列表")
    source_lang: str | None = Field(None, description="源语言（可选，用于已有字幕的翻译）")

    @field_validator("filepath")
    @classmethod
    def validate_filepath(cls, v: str) -> str:
        """验证文件存在"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"File does not exist: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return str(path.resolve())


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/scan", response_model=ScanDirectoryResponse)
async def scan_directory(
    request: ScanDirectoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ScanDirectoryResponse:
    """
    扫描指定目录以查找媒体文件和字幕

    返回媒体文件列表及其字幕语言信息和缺失的语言
    """
    try:
        # 使用请求中的语言，或从自动翻译规则推断
        if request.required_langs:
            required_langs = request.required_langs
        else:
            from app.services.detector import get_required_langs_from_rules

            required_langs = get_required_langs_from_rules(db)

        scanner = LocalMediaScanner()
        media_files = scanner.scan_directory(
            directory=request.directory,
            required_langs=required_langs,
            recursive=request.recursive,
            max_depth=request.max_depth,
        )

        # 转换为响应格式
        media_responses = [
            MediaFileResponse(
                filepath=mf.filepath,
                filename=mf.filename,
                size_bytes=mf.size_bytes,
                existing_subtitle_langs=mf.existing_subtitle_langs,
                missing_languages=mf.missing_languages,
                subtitle_files=mf.subtitle_files,
            )
            for mf in media_files
        ]

        logger.info(f"Scanned directory {request.directory}: found {len(media_files)} media files")

        return ScanDirectoryResponse(
            directory=request.directory,
            media_files=media_responses,
            total_count=len(media_files),
            required_langs=required_langs,
        )

    except PermissionError as e:
        raise HTTPException(
            status_code=403, detail=f"Permission denied accessing directory: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error scanning directory: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to scan directory: {str(e)}")


@router.get("/stats", response_model=DirectoryStatsResponse)
async def get_directory_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    directory: str = Query(..., description="目录路径"),
    recursive: bool = Query(True, description="是否递归统计"),
) -> DirectoryStatsResponse:
    """
    获取目录统计信息（不进行完整分析）

    快速返回媒体文件数量、大小等统计数据
    """
    try:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")

        scanner = LocalMediaScanner()

        total_media = 0
        total_size = 0
        total_subtitles = 0
        format_counts: dict[str, int] = {}

        def count_files(p: Path, depth: int = 0):
            nonlocal total_media, total_size, total_subtitles

            if depth > 5:  # 防止过深递归
                return

            try:
                for item in p.iterdir():
                    if item.is_file():
                        ext = item.suffix.lower()
                        if ext in scanner.VIDEO_EXTENSIONS:
                            total_media += 1
                            total_size += item.stat().st_size
                            format_counts[ext] = format_counts.get(ext, 0) + 1
                        elif ext in scanner.SUBTITLE_EXTENSIONS:
                            total_subtitles += 1
                    elif item.is_dir() and recursive:
                        count_files(item, depth + 1)
            except PermissionError:
                pass

        count_files(path)

        return DirectoryStatsResponse(
            directory=directory,
            total_media_files=total_media,
            total_size_bytes=total_size,
            total_subtitle_files=total_subtitles,
            video_formats=format_counts,
        )

    except Exception as e:
        logger.error(f"Error getting directory stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get directory stats: {str(e)}")


@router.post("/jobs", response_model=JobResponse)
async def create_local_media_job(
    request: CreateLocalJobRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    为本地媒体文件创建翻译任务

    - 如果指定了 source_lang，则直接翻译已有字幕
    - 如果未指定，则先执行 ASR 再翻译
    """
    try:
        filepath = Path(request.filepath)

        # 检查文件是否存在字幕
        scanner = LocalMediaScanner()
        subtitle_langs, _ = scanner._find_subtitle_languages(filepath)

        # 创建任务
        for target_lang in request.target_langs:
            # 确定任务类型
            if request.source_lang:
                # 指定了源语言，直接翻译
                if request.source_lang not in subtitle_langs:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Source language '{request.source_lang}' subtitle not found",
                    )

                from app.core.settings_helper import get_default_mt_model

                job = TranslationJob(
                    item_id=str(filepath),  # 使用文件路径作为 item_id
                    source_type="subtitle",  # 有源语言说明有字幕文件
                    source_path=str(filepath),  # 媒体文件路径
                    source_lang=request.source_lang,
                    target_langs=json.dumps([target_lang]),
                    model=get_default_mt_model(),
                    status="pending",
                )
                db.add(job)
                db.commit()
                db.refresh(job)

                # 提交 Celery 任务
                translate_subtitle_task.apply_async(args=[str(job.id)], queue="translate")

            else:
                # 未指定源语言，需要先 ASR
                job = TranslationJob(
                    item_id=str(filepath),
                    source_type="media",  # 需要 ASR 说明是媒体文件
                    source_path=str(filepath),  # 媒体文件路径
                    source_lang="auto",  # ASR 会自动检测
                    target_langs=json.dumps([target_lang]),
                    model=get_default_mt_model(),
                    status="pending",
                )
                db.add(job)
                db.commit()
                db.refresh(job)

                # 提交 Celery 任务
                asr_then_translate_task.apply_async(args=[str(job.id)], queue="asr")

        logger.info(f"Created job for local file {filepath.name}: targets={request.target_langs}")

        return JobResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating local media job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.post("/batch-jobs", response_model=list[JobResponse])
async def create_batch_local_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    filepaths: list[str] = Query(..., description="媒体文件路径列表"),
    target_langs: list[str] = Query(..., description="目标语言列表"),
    source_lang: str | None = Query(None, description="源语言（可选）"),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    """
    批量创建本地媒体文件翻译任务
    """
    jobs = []

    for filepath_str in filepaths:
        try:
            request = CreateLocalJobRequest(
                filepath=filepath_str, target_langs=target_langs, source_lang=source_lang
            )
            job = await create_local_media_job(request, db)
            jobs.append(job)
        except Exception as e:
            logger.error(f"Failed to create job for {filepath_str}: {str(e)}")
            continue

    return jobs
