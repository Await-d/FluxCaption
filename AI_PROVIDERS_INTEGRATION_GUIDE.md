# 多AI平台集成指南

FluxCaption 现已支持多个AI平台,包括本地部署和云服务。

## 支持的AI平台

### 1. Ollama (本地部署)
- **提供者名称**: `ollama`
- **特点**: 完全本地运行,隐私友好,支持模型下载
- **推荐模型**: qwen2.5:7b-instruct, llama3, mistral
- **配置示例**:
```env
OLLAMA_BASE_URL=http://localhost:11434
```

### 2. OpenAI
- **提供者名称**: `openai`
- **特点**: 强大的GPT系列模型
- **推荐模型**: gpt-4-turbo, gpt-3.5-turbo
- **配置示例**:
```json
{
  "provider_name": "openai",
  "api_key": "sk-xxxxxxxxxxxx",
  "base_url": "https://api.openai.com/v1"
}
```

### 3. DeepSeek
- **提供者名称**: `deepseek`
- **特点**: 性价比极高,中文友好
- **推荐模型**: deepseek-chat, deepseek-coder
- **定价**: ¥1/百万tokens (输入), ¥2/百万tokens (输出)
- **配置示例**:
```json
{
  "provider_name": "deepseek",
  "api_key": "sk-xxxxxxxxxxxx",
  "base_url": "https://api.deepseek.com/v1"
}
```

### 4. Claude (Anthropic)
- **提供者名称**: `claude`
- **特点**: 超长上下文,优秀的推理能力
- **推荐模型**: claude-3-5-sonnet, claude-3-haiku (经济型)
- **配置示例**:
```json
{
  "provider_name": "claude",
  "api_key": "sk-ant-xxxxxxxxxxxx",
  "base_url": "https://api.anthropic.com/v1"
}
```

### 5. Gemini (Google)
- **提供者名称**: `gemini`
- **特点**: Google最新AI模型
- **推荐模型**: gemini-pro
- **配置示例**:
```json
{
  "provider_name": "gemini",
  "api_key": "AIzaxxxxxxxxxx"
}
```

### 6. 智谱AI (GLM)
- **提供者名称**: `zhipu`
- **特点**: 中文优化,GLM-4性能强劲
- **推荐模型**: glm-4, glm-4-flash (免费)
- **配置示例**:
```json
{
  "provider_name": "zhipu",
  "api_key": "xxxxxxxxxxxx.xxxxxxxx",
  "base_url": "https://open.bigmodel.cn/api/paas/v4"
}
```

### 7. Moonshot AI (Kimi)
- **提供者名称**: `moonshot`
- **特点**: 超长上下文 (最高128K)
- **推荐模型**: moonshot-v1-32k, moonshot-v1-128k
- **配置示例**:
```json
{
  "provider_name": "moonshot",
  "api_key": "sk-xxxxxxxxxxxx",
  "base_url": "https://api.moonshot.cn/v1"
}
```

### 8. 自定义 OpenAI 兼容端点
- **提供者名称**: `custom_openai`
- **特点**: 支持任何OpenAI兼容API
- **支持平台**: OpenRouter, Together AI, LocalAI, vLLM, Text Generation WebUI
- **配置示例**:
```json
{
  "provider_name": "custom_openai",
  "api_key": "your-api-key",
  "base_url": "https://openrouter.ai/api/v1"
}
```

## 使用方式

### 1. 通过数据库配置 (推荐)

在 `ai_provider_configs` 表中添加配置:

```sql
INSERT INTO ai_provider_configs (
    id, provider_name, display_name, is_enabled,
    api_key, base_url, default_model, priority
) VALUES (
    'uuid-here',
    'deepseek',
    'DeepSeek',
    true,
    'sk-your-api-key',
    'https://api.deepseek.com/v1',
    'deepseek-chat',
    2
);
```

### 2. 通过 API 配置

```bash
# 添加/更新提供者配置
POST /api/ai-providers
{
  "provider_name": "deepseek",
  "display_name": "DeepSeek",
  "is_enabled": true,
  "api_key": "sk-your-api-key",
  "base_url": "https://api.deepseek.com/v1",
  "default_model": "deepseek-chat"
}

# 列出所有提供者
GET /api/ai-providers

# 测试提供者连接
POST /api/ai-providers/{provider_name}/health-check
```

### 3. 使用模型标识符

在创建翻译任务时,使用 `provider:model` 格式:

```json
{
  "source_lang": "en",
  "target_langs": ["zh-CN"],
  "model": "deepseek:deepseek-chat"
}
```

或者直接使用模型名(系统会自动识别):

```json
{
  "model": "gpt-4"  // 自动识别为 openai:gpt-4
}
```

## 代码集成示例

### Python 后端使用

```python
from app.services.unified_ai_client import get_unified_ai_client
from app.core.db import session_scope

# 使用统一客户端
with session_scope() as session:
    ai_client = get_unified_ai_client(session)

    # 方式1: 使用完整模型标识符
    response = await ai_client.generate(
        model="deepseek:deepseek-chat",
        prompt="Translate to Chinese: Hello, world!",
        temperature=0.3
    )

    # 方式2: 只用模型名(自动推断提供者)
    response = await ai_client.generate(
        model="gpt-4",
        prompt="Translate to Chinese: Hello, world!"
    )

    print(response.text)
```

### 直接使用特定提供者

```python
from app.services.ai_providers.deepseek_provider import DeepSeekProvider

provider = DeepSeekProvider(
    api_key="sk-your-key",
    base_url="https://api.deepseek.com/v1"
)

response = await provider.generate(
    model="deepseek-chat",
    prompt="Translate: Hello",
    temperature=0.3
)
```

## 成本对比 (2025年1月)

| 提供者 | 模型 | 输入 (¥/百万tokens) | 输出 (¥/百万tokens) | 推荐场景 |
|--------|------|---------------------|---------------------|----------|
| Ollama | qwen2.5:7b | 免费 | 免费 | 本地部署,隐私敏感 |
| DeepSeek | deepseek-chat | 1 | 2 | 高性价比,中文优化 |
| 智谱AI | glm-4-flash | 0 | 0 | 免费额度,测试开发 |
| OpenAI | gpt-3.5-turbo | 3.5 | 7 | 平衡性能和成本 |
| OpenAI | gpt-4-turbo | 70 | 210 | 最高质量要求 |
| Claude | claude-3-haiku | 1.75 | 8.75 | 经济型,快速响应 |
| Claude | claude-3-5-sonnet | 21 | 105 | 复杂推理任务 |
| Moonshot | moonshot-v1-32k | 168 | 168 | 超长上下文 |

## 性能优化建议

### 1. 使用合适的模型

- **短字幕翻译** (< 100字): 使用快速模型 (gpt-3.5-turbo, deepseek-chat, glm-4-flash)
- **长文本翻译**: 使用大上下文模型 (moonshot-v1-128k, claude-3-sonnet)
- **专业术语**: 使用高质量模型 (gpt-4, claude-3-5-sonnet)

### 2. 启用缓存

系统自动缓存相同文本的翻译结果,避免重复调用API。

### 3. 批量处理

调整 `translation_batch_size` 参数以优化吞吐量:

```env
TRANSLATION_BATCH_SIZE=10  # 每批处理的字幕行数
```

### 4. 温度参数调优

```python
# 翻译任务推荐使用较低温度
temperature = 0.3  # 更稳定,更准确

# 创意任务可以提高温度
temperature = 0.7
```

## 故障排查

### 问题1: 提供者连接失败

```bash
# 检查健康状态
curl http://localhost:8000/api/ai-providers/deepseek/health-check

# 查看日志
docker logs fluxcaption-api
```

### 问题2: API Key 无效

- 检查 API Key 格式是否��确
- 确认 API Key 有足够余额
- 验证 base_url 是否正确

### 问题3: 模型不存在

```python
# 列出可用模型
from app.services.ai_providers.factory import provider_manager

provider = provider_manager.get_provider("deepseek", config={
    "api_key": "your-key"
})
models = await provider.list_models()
print([m.id for m in models])
```

## 安全建议

1. **API Key 管理**
   - 不要在代码中硬编码 API Key
   - 使用环境变量或数据库加密存储
   - 定期轮换 API Key

2. **访问控制**
   - 限制API访问IP白名单
   - 使用最小权限原则
   - 监控API调用量

3. **数据隐私**
   - 敏感内容优先使用本地 Ollama
   - 了解各平台的数据保留政策
   - 考虑使用自托管方案

## 下一步

- [ ] 在前端添加提供者管理界面
- [ ] 实现成本预估和预算控制
- [ ] 添加更多提供者 (Cohere, Mistral AI, etc.)
- [ ] 支持模型性能基准测试
