# AetherPackBot 更新日志

## v1.1.1 - 核心消息管线修复 (2026-02-07)

### 🐛 Bug 修复

#### 消息管线断路修复（关键）
- **修复 LLM 无法调用**：EventDispatcher 没有注册 MessageProcessor 作为 MESSAGE_RECEIVED 事件的处理器，导致平台消息进入事件队列后无人消费，LLM 永远不会被调用。参考 AstrBot 的 EventBus.dispatch() 机制，在 app_kernel 中将 MessageProcessor.process 注册为事件处理器。

#### QQ OneBot 适配器增强
- **修复 @bot 检测**：解析 OneBot `at` 消息段，对比 self_id 判断是否 @了机器人。连接时从 lifecycle 事件和 get_login_info() 获取机器人 QQ 号。参考 AstrBot 的 convert_message()。
- **新增消息段解析**：支持 `at`（@某人）、`reply`（回复引用）、`face`（表情）消息段。
- **修复回复消息格式**：`_convert_chain_to_onebot` 新增 MentionComponent → `at` 段、ReplyComponent → `reply` 段的转换。

#### 唤醒机制重构（参考 AstrBot WakingCheckStage）
- **唤醒前缀裁剪**：匹配 wake_prefix 后自动去除前缀（如 `/help` → `help`），避免 LLM 收到带前缀的原始文本。
- **唤醒优先级**：按 @bot → wake_prefix → wake_words → 私聊 的顺序依次检测。
- **干净文本传递**：裁剪后的文本通过 PipelineContext.metadata 传递给 AgentProcessingStage，再传给 AgentOrchestrator。

#### LLM Provider 工具调用修复
- **修复 OpenAI/兼容接口的消息构建**：tool_calls 和 tool_call_id 字段没有被传递给 API，导致工具调用循环失败。新增 `_build_openai_messages()` 方法正确构建完整消息格式。

#### 错误提示改进
- LLM Provider 未配置时返回友好中文提示，而非静默失败。
- Agent 处理阶段增加日志输出，方便排查问题。

---

## v1.1.0 - Dashboard 全面重建 (2026-02-07)

### 🎨 全新 Dashboard

完全重写前端控制台，对标 AstrBot 功能集，包含 8 个功能页面：

#### 📊 仪表盘
- 统计卡片：平台数、提供商数、插件数、运行时间
- 系统资源监控：CPU 使用率（含进度条）、内存占用
- 快速操作入口：一键跳转聊天、添加模型、添加平台
- 每 10 秒自动刷新

#### 📱 消息平台管理
- 平台 CRUD：添加 / 编辑 / 删除消息平台
- 启停控制：一键启动或停止平台适配器
- 支持 4 种平台类型：Telegram、Discord、QQ OneBot v11、QQ 官方
- OneBot 专属配置：反向 WS 监听地址 + 端口
- 空状态提示 + 错误展示

#### ✨ 模型提供商管理
- 支持 13 种提供商类型：OpenAI、Anthropic、Gemini、DeepSeek、Moonshot、Groq、Ollama、SiliconFlow、智谱、Mistral、xAI、LM Studio、OpenAI 兼容
- 添加时自动填充默认模型和 API 地址
- 按类型动态显示/隐藏 API Key 输入框（Ollama、LM Studio 无需 Key）
- 可选模型列表提示
- 设为默认提供商
- 健康检测（🩺 按钮一键测试连通性）
- 创建失败时显示具体错误（含缺少依赖包提示）

#### ❤️ 人格管理（新增独立页面）
- 人格 CRUD：新建 / 编辑 / 删除人格配置
- 设为默认人格
- System Prompt 预览（折叠展示，最多 500 字）
- 当前使用人格高亮标记
- 聊天时自动注入默认人格的 System Prompt

#### 🧩 扩展插件
- 插件列表：名称、版本、作者、描述、状态
- 一键重载插件

#### 💬 在线聊天
- 选择提供商下拉框（可切换不同 LLM 对话）
- 聊天历史回溯（从数据库加载最近 50 条）
- Ctrl+Enter 快捷发送
- 乐观 UI 更新（消息立即显示，不等响应）
- 错误消息内联展示

#### ⚙️ 系统设置（4 个标签页）
- **基本设置**：机器人昵称、唤醒前缀、默认提供商
- **Web 服务**：监听地址、端口（重启生效）
- **回复设置**：@发送者、引用原消息、添加前缀、前缀模板
- **账号管理**：修改管理员用户名和密码

#### 📜 控制台日志
- 彩色日志等级（ERROR 红 / WARNING 黄 / INFO 蓝 / DEBUG 灰）
- 时间戳 + 模块名显示
- 自动滚动开关
- 每 5 秒自动刷新

---

### 🔧 后端修复与增强

#### API 错误处理
- `api()` 函数自动检测 HTTP 错误和 `status: "error"` 响应并抛出异常，不再静默失败
- 提供商创建 500 错误修复：捕获 `ImportError`，返回友好提示 "缺少依赖包 xxx，请运行: pip install xxx"

#### 配置保存深度合并
- `PUT /api/config` 改为深度合并（`_deep_merge`），修改密码不再丢失 host/port 等字段

#### 状态 API 增强
- `/api/status` 新增 `cpu_percent`、`memory_mb`、`uptime` 字段（基于 psutil）

#### 字段一致性修复
- 提供商字段统一：`api_base_url`（非 `base_url`）、`model`（非 `default_model`）
- 回复设置字段统一：`quote_original`（非 `quote`）
- 平台状态映射统一：`running` / `stopped`（非枚举名 `CONNECTED` / `DISCONNECTED`）
- 提供商显示名统一：`display_name`（非 `p.name`）

#### 其他修复
- 移除 `add_provider` 中重复的 ID 赋值
- 平台空 ID 自动生成
- `register_platform_type` 缩进错误修复（从类内移到模块级）
- 登录路由修复：`/api/login` → `/api/auth/login`

---

### 🆕 OneBot v11 适配器

- 新增 `qq_onebot.py`：通过 aiocqhttp 实现 QQ OneBot v11 协议
- 支持反向 WebSocket 连接（NAPCat / Go-CQHttp）
- 在平台管理中注册为可选类型

---

### 📁 文件变更

| 文件 | 操作 |
|---|---|
| `data/dist_v2/index.html` | 重写 |
| `data/dist_v2/js/app.js` | 重写 |
| `data/dist_v2/css/style.css` | 更新（新增 modal/notification/btn-danger 样式） |
| `aetherpackbot/webapi/server.py` | 多处修复（错误处理、深度合并、状态增强） |
| `aetherpackbot/platforms/manager.py` | 修复缩进、ID 生成、状态映射 |
| `aetherpackbot/platforms/qq_onebot.py` | 新增 |
| `aetherpackbot/providers/manager.py` | 字段名修复、get_status_list 完善 |
