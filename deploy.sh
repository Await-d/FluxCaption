#!/bin/bash

# =============================================================================
# FluxCaption Docker 部署脚本
# =============================================================================
# 功能：构建和部署 FluxCaption 服务
# 作者：FluxCaption Team
# 最后更新：2025-10-09
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示横幅
show_banner() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║                                                       ║"
    echo "║             FluxCaption 部署工具 v1.0                ║"
    echo "║   AI-Powered Subtitle Translation for Jellyfin       ║"
    echo "║                                                       ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
}

# 检查必需的命令
check_requirements() {
    info "检查系统依赖..."

    local missing_deps=()

    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_deps+=("docker-compose")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "缺少必需的依赖: ${missing_deps[*]}"
        echo ""
        echo "请安装缺失的依赖后重试："
        echo "  Ubuntu/Debian: sudo apt-get install docker.io docker-compose"
        echo "  CentOS/RHEL:   sudo yum install docker docker-compose"
        exit 1
    fi

    success "系统依赖检查通过"
}

# 检查 .env 文件
check_env_file() {
    info "检查环境配置文件..."

    if [ ! -f .env ]; then
        warn ".env 文件不存在，从 .env.example 创建..."
        if [ -f .env.example ]; then
            cp .env.example .env
            warn "请编辑 .env 文件，填入必需的配置值"
            warn "特别是以下配置："
            echo "  - JELLYFIN_API_KEY"
            echo "  - OLLAMA_BASE_URL"
            echo ""
            read -p "按 Enter 键继续，或 Ctrl+C 取消..."
        else
            error ".env.example 文件不存在，无法创建配置"
            exit 1
        fi
    else
        success "环境配置文件存在"
    fi
}

# 停止现有服务
stop_services() {
    info "停止现有服务..."

    if docker compose ps | grep -q "Up"; then
        docker compose down
        success "现有服务已停止"
    else
        info "没有运行中的服务"
    fi
}

# 清理旧镜像（可选）
cleanup_old_images() {
    if [ "$1" = "--cleanup" ]; then
        info "清理未使用的 Docker 镜像..."
        docker image prune -f
        success "清理完成"
    fi
}

# 构建镜像
build_images() {
    local no_cache=""
    if [ "$1" = "--no-cache" ]; then
        no_cache="--no-cache"
        info "使用 --no-cache 构建镜像..."
    else
        info "构建 Docker 镜像..."
    fi

    # 构建 backend（包含前端）
    info "构建 backend 镜像..."
    docker compose build $no_cache backend

    # 构建 beat
    info "构建 beat 镜像..."
    docker compose build $no_cache beat

    success "所有镜像构建完成"
}

# 启动服务
start_services() {
    info "启动 Docker Compose 服务..."

    docker compose up -d

    success "服务启动成功"
}

# 等待服务就绪
wait_for_services() {
    info "等待服务启动..."

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker compose ps | grep -q "healthy"; then
            success "服务已就绪"
            return 0
        fi

        echo -n "."
        sleep 2
        ((attempt++))
    done

    warn "服务启动超时，请检查日志"
    return 1
}

# 显示服务状态
show_status() {
    echo ""
    info "服务状态："
    docker compose ps
    echo ""
}

# 显示访问信息
show_access_info() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║                   部署成功！                          ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
    info "访问地址："
    echo "  Web 界面:     http://localhost"
    echo "  API 文档:     http://localhost/docs"
    echo "  API Redoc:    http://localhost/redoc"
    echo ""
    info "默认登录信息："
    echo "  用户名: admin"
    echo "  密码:   admin123"
    echo ""
    warn "⚠️  首次登录后请立即修改密码！"
    echo ""
    info "常用命令："
    echo "  查看日志:     ./logs.sh"
    echo "  重启服务:     ./restart.sh"
    echo "  停止服务:     ./stop.sh"
    echo "  清理数据:     ./cleanup.sh"
    echo ""
}

# 主函数
main() {
    show_banner

    # 解析参数
    local no_cache=""
    local cleanup=""
    local skip_build=false

    for arg in "$@"; do
        case $arg in
            --no-cache)
                no_cache="--no-cache"
                ;;
            --cleanup)
                cleanup="--cleanup"
                ;;
            --skip-build)
                skip_build=true
                ;;
            --help|-h)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --no-cache      不使用 Docker 缓存构建"
                echo "  --cleanup       清理未使用的 Docker 镜像"
                echo "  --skip-build    跳过构建，直接启动服务"
                echo "  --help, -h      显示此帮助信息"
                echo ""
                exit 0
                ;;
        esac
    done

    # 执行部署步骤
    check_requirements
    check_env_file
    stop_services
    cleanup_old_images $cleanup

    if [ "$skip_build" = false ]; then
        build_images $no_cache
    else
        info "跳过构建步骤"
    fi

    start_services
    wait_for_services
    show_status
    show_access_info
}

# 错误处理
trap 'error "部署过程中发生错误"; exit 1' ERR

# 执行主函数
main "$@"
