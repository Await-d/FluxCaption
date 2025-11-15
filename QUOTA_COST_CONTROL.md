# AI提供者额度和成本控制

## 功能概述

FluxCaption 现已支持完整的云服务AI额度限制和消费记录功能,防止意外高额费用。

## 核心功能

### 1. 额度限制
- **每日限额**: 设置每天最大消费金额 (USD)
- **每月限额**: 设置每月最大消费金额 (USD)
- **Token限制**: 限制每日/每月最大Token使用量
- **请求频率**: 限制每分钟/每小时请求次数
- **自动禁用**: 达到限额后自动禁用提供者

### 2. 消费记录
- **详细日志**: 记录每次API调用的完整信息
- **成本计算**: 自动计算输入/输出token成本
- **性能监控**: 跟踪响应时间、错误率
- **审计追踪**: job_id、user_id关联追踪

### 3. 预警机制
- **阈值告警**: 达到80%额度时发送告警
- **自动禁用**: 超额后自动禁用提供者(可配置)
- **邮件通知**: TODO - 集成邮件告警

## 数据库表结构

### ai_provider_quotas (额度配置)
```sql
provider_name         -- 提供者名称
daily_limit          -- 每日限额 (USD)
monthly_limit        -- 每月限额 (USD)
current_daily_cost   -- 当前每日消费
current_monthly_cost -- 当前每月消费
alert_threshold_percent -- 告警阈值 (默认80%)
auto_disable_on_limit   -- 超额自动禁用
```

### ai_provider_usage_logs (消费日志)
```sql
provider_name    -- 提供者
model_name       -- 模型
job_id           -- 关联任务ID
input_tokens     -- 输入token数
output_tokens    -- 输出token数
input_cost       -- 输入成本
output_cost      -- 输出成本
total_cost       -- 总成本
response_time_ms -- 响应时间
is_error         -- 是否错误
```

## 使用方式

### 1. 配置额度限制

#### 方式A: 直接SQL
```sql
INSERT INTO ai_provider_quotas (
    id, provider_name, daily_limit, monthly_limit,
    alert_threshold_percent, auto_disable_on_limit
) VALUES (
    'uuid-here',
    'openai',
    10.0,   -- 每天最多$10
    100.0,  -- 每月最多$100
    80,     -- 80%时告警
    true    -- 超额自动禁用
);
```

#### 方式B: 通过代码
```python
from app.models.ai_provider_usage import AIProviderQuota
from app.core.db import session_scope

with session_scope() as session:
    quota = AIProviderQuota(
        provider_name="deepseek",
        daily_limit=5.0,    # $5/天
        monthly_limit=50.0, # $50/月
        alert_threshold_percent=80,
        auto_disable_on_limit=True,
    )
    session.add(quota)
    session.commit()
```

### 2. 查看消费记录

```python
from app.services.ai_quota_service import AIQuotaService
from datetime import datetime, timedelta

with session_scope() as session:
    quota_service = AIQuotaService(session)

    # 查看今日统计
    today = datetime.now() - timedelta(days=1)
    stats = quota_service.get_usage_stats(
        provider_name="openai",
        start_date=today
    )

    print(f"Total cost: ${stats['total_cost']:.4f}")
    print(f"Total requests: {stats['total_requests']}")
```

### 3. 查询详细日志

```sql
-- 查看今日所有消费
SELECT
    provider_name,
    model_name,
    SUM(total_cost) as daily_cost,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens
FROM ai_provider_usage_logs
WHERE DATE(created_at) = CURDATE()
GROUP BY provider_name, model_name;

-- 查看特定任务的消费
SELECT * FROM ai_provider_usage_logs
WHERE job_id = 'your-job-id'
ORDER BY created_at;

-- 查看错误记录
SELECT
    provider_name,
    model_name,
    error_message,
    COUNT(*) as error_count
FROM ai_provider_usage_logs
WHERE is_error = true
GROUP BY provider_name, model_name, error_message;
```

## 成本计算示例

系统会根据 `model_registry` 表中的价格自动计算成本:

```python
# 示例: GPT-4 调用
# input_tokens: 1000, output_tokens: 500
# cost_input_per_1k: $0.03, cost_output_per_1k: $0.06

input_cost = (1000 / 1000) * 0.03 = $0.03
output_cost = (500 / 1000) * 0.06 = $0.03
total_cost = $0.06

# 记录到 ai_provider_usage_logs
```

## 额度检查流程

```
1. 用户请求翻译
   ↓
2. UnifiedAIClient.generate()
   ↓
3. QuotaService.check_quota()
   ├─ 检查每日额度
   ├─ 检查每月额度
   └─ 超额 → 抛出 QuotaExceededException
   ↓
4. 执行API调用
   ↓
5. QuotaService.log_usage()
   ├─ 计算成本
   ├─ 保存日志
   └─ 更新额度计数器
```

## 监控和告警

### 检查额度使用情况
```python
from app.models.ai_provider_usage import AIProviderQuota

with session_scope() as session:
    quota = session.query(AIProviderQuota).filter_by(
        provider_name="openai"
    ).first()

    print(f"每日使用: ${quota.current_daily_cost:.2f} / ${quota.daily_limit:.2f}")
    print(f"每月使用: ${quota.current_monthly_cost:.2f} / ${quota.monthly_limit:.2f}")
    print(f"使用率: {quota.get_usage_percent('daily'):.1f}%")

    if quota.is_limit_exceeded():
        print("⚠️ 额度已超限!")
```

### 生成消费报表
```sql
-- 每日消费趋势
SELECT
    DATE(created_at) as date,
    provider_name,
    SUM(total_cost) as daily_cost,
    COUNT(*) as requests
FROM ai_provider_usage_logs
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(created_at), provider_name
ORDER BY date DESC;

-- 模型使用排行
SELECT
    model_name,
    COUNT(*) as usage_count,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost) as total_cost,
    AVG(response_time_ms) as avg_response_time
FROM ai_provider_usage_logs
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY model_name
ORDER BY total_cost DESC
LIMIT 10;
```

## 最佳实践

### 1. 设置合理的限额
```python
# 开发环境
daily_limit = 5.0    # $5/天
monthly_limit = 50.0 # $50/月

# 生产环境
daily_limit = 50.0    # $50/天
monthly_limit = 1000.0 # $1000/月
```

### 2. 定期审查消费
- 每周检查消费趋势
- 识别异常消费模式
- 优化模型选择

### 3. 成本优化建议
- 短文本使用便宜模型 (deepseek, glm-4-flash)
- 批量处理减少请求次数
- 启用翻译缓存避免重复调用
- 优先使用本地Ollama

### 4. 监控告警
```python
# 设置告警阈值为70%
quota.alert_threshold_percent = 70

# 禁用自动禁用(手动审查)
quota.auto_disable_on_limit = False
```

## 故障排查

### 问题1: 额度检查失败
```bash
# 检查quota记录是否存在
SELECT * FROM ai_provider_quotas WHERE provider_name = 'openai';

# 手动重置计数器
UPDATE ai_provider_quotas
SET current_daily_cost = 0,
    current_monthly_cost = 0,
    daily_reset_at = NOW(),
    monthly_reset_at = NOW()
WHERE provider_name = 'openai';
```

### 问题2: 成本计算不准确
```bash
# 检查模型价格配置
SELECT provider, name, cost_input_per_1k, cost_output_per_1k
FROM model_registry
WHERE provider = 'openai';

# 更新价格
UPDATE model_registry
SET cost_input_per_1k = 0.03,
    cost_output_per_1k = 0.06
WHERE provider = 'openai' AND name = 'gpt-4';
```

### 问题3: 日志记录失败
- 检查数据库连接
- 确认表结构正确
- 查看应用日志: `docker logs fluxcaption-api`

## 环境变量配置

```env
# 全局成本控制
MAX_MONTHLY_COST=100.0

# 单次请求最大token
MAX_TOKENS_PER_TRANSLATION=4096

# 是否启用成本预估
ENABLE_COST_ESTIMATION=true

# 告警阈值
COST_ALERT_THRESHOLD_PERCENT=80
```

## API端点 (待实现)

```bash
# 查看额度使用情况
GET /api/ai-providers/{provider}/quota

# 更新额度配置
PUT /api/ai-providers/{provider}/quota

# 查看消费日志
GET /api/ai-providers/{provider}/usage-logs?start_date=2025-01-01

# 生成消费报表
GET /api/ai-providers/usage-report?period=monthly
```
