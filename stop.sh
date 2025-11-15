#!/bin/bash

# =============================================================================
# FluxCaption 停止脚本
# =============================================================================
# 功能：停止 FluxCaption 所有服务
# =============================================================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "═══════════════════════════════════════"
echo "  停止 FluxCaption 服务"
echo "═══════════════════════════════════════"
echo ""

# 检查服务是否在运行
if ! docker compose ps | grep -q "Up"; then
    info "没有运行中的服务"
    exit 0
fi

info "停止所有服务..."
docker compose down

success "所有服务已停止"

# 显示剩余容器（如果有）
if docker compose ps | grep -q "fluxcaption"; then
    error "部分容器仍在运行:"
    docker compose ps
else
    info "所有容器已清理"
fi

echo ""
