#!/bin/bash

# =============================================================================
# FluxCaption 清理脚本
# =============================================================================
# 功能：清理 Docker 资源和数据
# 警告：此操作会删除所有数据，请谨慎使用！
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --all           完全清理 (容器、卷、镜像、网络)"
    echo "  --containers    仅清理容器"
    echo "  --volumes       清理容器和卷 (会删除数据库数据!)"
    echo "  --images        清理容器和镜像"
    echo "  --cache         清理 Docker 构建缓存"
    echo "  --help, -h      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --containers    # 仅停止并删除容器"
    echo "  $0 --all           # 完全清理所有资源"
    echo ""
}

# 确认操作
confirm() {
    local prompt="$1"
    warn "$prompt"
    warn "此操作不可逆，确定继续吗？(yes/no)"
    read -r response
    if [ "$response" != "yes" ]; then
        info "操作已取消"
        exit 0
    fi
}

# 清理容器
cleanup_containers() {
    info "停止并删除所有容器..."
    docker compose down
    success "容器已清理"
}

# 清理卷
cleanup_volumes() {
    info "删除所有数据卷..."
    warn "⚠️  这将删除所有数据库数据、上传的文件等！"
    docker compose down -v
    success "数据卷已清理"
}

# 清理镜像
cleanup_images() {
    info "删除 FluxCaption 镜像..."

    # 删除项目镜像
    local images=$(docker images | grep "fluxcaption" | awk '{print $3}')
    if [ -n "$images" ]; then
        echo "$images" | xargs docker rmi -f
        success "项目镜像已删除"
    else
        info "没有找到项目镜像"
    fi
}

# 清理网络
cleanup_networks() {
    info "删除 Docker 网络..."
    docker compose down --remove-orphans
    success "网络已清理"
}

# 清理构建缓存
cleanup_cache() {
    info "清理 Docker 构建缓存..."
    docker builder prune -f
    success "构建缓存已清理"
}

# 清理未使用的资源
cleanup_unused() {
    info "清理未使用的 Docker 资源..."
    docker system prune -f
    success "未使用的资源已清理"
}

# 完全清理
cleanup_all() {
    confirm "⚠️  完全清理将删除所有容器、数据卷、镜像和网络！"

    cleanup_containers
    cleanup_volumes
    cleanup_images
    cleanup_networks
    cleanup_cache
    cleanup_unused

    success "完全清理完成"

    # 显示磁盘空间统计
    echo ""
    info "Docker 磁盘使用情况："
    docker system df
}

echo ""
echo "═══════════════════════════════════════"
echo "  FluxCaption 清理工具"
echo "═══════════════════════════════════════"
echo ""

# 解析参数
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

case "$1" in
    --all)
        cleanup_all
        ;;
    --containers)
        confirm "确定要删除所有容器吗？"
        cleanup_containers
        ;;
    --volumes)
        confirm "⚠️  确定要删除所有数据卷吗？这将删除所有数据！"
        cleanup_containers
        cleanup_volumes
        ;;
    --images)
        confirm "确定要删除所有镜像吗？"
        cleanup_containers
        cleanup_images
        ;;
    --cache)
        info "清理 Docker 缓存..."
        cleanup_cache
        cleanup_unused
        ;;
    --help|-h)
        show_help
        ;;
    *)
        error "未知选项: $1"
        show_help
        exit 1
        ;;
esac

echo ""
