# AetherPackBot

Multi-platform LLM chatbot and development framework.

## Features

- 🤖 Multi-LLM support: OpenAI, Anthropic, Google Gemini, and more
- 📱 Multi-platform: Telegram, Discord, QQ, Slack, DingTalk, Lark
- 🔌 Plugin system: Extensible plugin architecture
- 🧠 Agent system: Tool-calling with automatic orchestration
- 🌐 Web dashboard: Vue.js based management interface
- 💾 Persistent storage: SQLite with SQLAlchemy ORM

## Quick Start

```bash
# Install dependencies
pip install uv
uv sync

# Run the bot
uv run main.py
```

## Architecture

```text
AETHERPACKBOT/
├── AetherPackBot/              # 主框架（纯 Python）
│   ├── cli/                    # AetherPackBot CLI 窗口（映射到 aetherpackbot.core.cli）
│   ├── core/                   # 框架核心（映射到 aetherpackbot.core.kernel）
│   ├── dashboard/              # 对接 WebUI（映射到 aetherpackbot.core.webapi）
│   └── api/                    # 对接所有 API（映射到 aetherpackbot.core.api）
├── dashboard/                  # WebUI 面板前端目录（预留）
├── data/                       # 运行后自动创建/生成数据文件
└── plugin/
    └── AetherPackBot/          # 基础指令与功能插件目录
```

> 说明：为保持兼容性，核心实现已迁移至 `aetherpackbot/core/`，上述 `AetherPackBot/*` 为对应命名空间映射与新目录结构入口。

## License

MIT License
