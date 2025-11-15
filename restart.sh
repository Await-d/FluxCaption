#!/bin/bash

# =============================================================================
# FluxCaption 重启脚本
# =============================================================================
# 功能：重启 FluxCaption 指定服务或所有服务
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
echo "  重启 FluxCaption 服务"
echo "═══════════════════════════════════════"
echo ""

# 解析参数
SERVICE=""
if [ $# -gt 0 ]; then
    SERVICE="$1"
fi

if [ -z "$SERVICE" ]; then
    # 重启所有服务
    info "重启所有服务..."
    docker compose restart
    success "所有服务已重启"
else
    # 重启指定服务
    info "重启服务: $SERVICE"
    docker compose restart "$SERVICE"
    success "服务 $SERVICE 已重启"
fi

echo ""
info "等待服务就绪..."
sleep 3

echo ""
info "服务状态："
if [ -z "$SERVICE" ]; then
    docker compose ps
else
    docker compose ps "$SERVICE"
fi

echo ""
success "重启完成"
echo ""
