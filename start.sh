#!/bin/bash

# =============================================================================
# FluxCaption 启动脚本
# =============================================================================
# 功能：启动 FluxCaption 所有服务
# =============================================================================

set -e

# 颜色定义
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

echo ""
echo "═══════════════════════════════════════"
echo "  启动 FluxCaption 服务"
echo "═══════════════════════════════════════"
echo ""

# 检查是否已在运行
if docker compose ps | grep -q "Up"; then
    warn "服务已在运行，是否重启? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        info "重启服务..."
        docker compose restart
        success "服务已重启"
    else
        info "取消操作"
        exit 0
    fi
else
    info "启动服务..."
    docker compose up -d
    success "服务启动成功"
fi

echo ""
info "等待服务就绪..."
sleep 3

echo ""
info "服务状态："
docker compose ps

echo ""
success "所有服务已启动"
echo ""
info "访问地址: http://localhost"
echo ""
