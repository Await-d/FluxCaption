#!/bin/bash

# =============================================================================
# FluxCaption 日志查看脚本
# =============================================================================
# 功能：查看 FluxCaption 服务日志
# =============================================================================

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

# 显示帮助
show_help() {
    echo "用法: $0 [服务名] [选项]"
    echo ""
    echo "服务名:"
    echo "  backend     - 后端 API 服务"
    echo "  beat        - Celery Beat 调度器"
    echo "  postgres    - PostgreSQL 数据库"
    echo "  redis       - Redis 缓存"
    echo "  ollama      - Ollama AI 模型服务"
    echo "  (留空)      - 所有服务"
    echo ""
    echo "选项:"
    echo "  -f, --follow    实时跟踪日志"
    echo "  -n <数量>       显示最后 N 行日志 (默认: 100)"
    echo "  -h, --help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 查看所有服务最后 100 行日志"
    echo "  $0 backend -f         # 实时跟踪 backend 日志"
    echo "  $0 backend -n 50      # 查看 backend 最后 50 行日志"
    echo ""
}

# 解析参数
SERVICE=""
FOLLOW=""
TAIL="100"

while [ $# -gt 0 ]; do
    case "$1" in
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n)
            TAIL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        backend|beat|postgres|redis|ollama)
            SERVICE="$1"
            shift
            ;;
        *)
            warn "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

echo ""
echo "═══════════════════════════════════════"
if [ -z "$SERVICE" ]; then
    echo "  查看所有服务日志"
else
    echo "  查看 $SERVICE 服务日志"
fi
echo "═══════════════════════════════════════"
echo ""

# 构建 docker compose logs 命令
CMD="docker compose logs"

if [ -n "$FOLLOW" ]; then
    CMD="$CMD -f"
    info "实时跟踪日志 (Ctrl+C 退出)"
else
    CMD="$CMD --tail=$TAIL"
    info "显示最后 $TAIL 行日志"
fi

if [ -n "$SERVICE" ]; then
    CMD="$CMD $SERVICE"
fi

echo ""

# 执行命令
eval $CMD
