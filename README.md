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

```
AETHERPACKBOT
├───AetherPackBot（主框架，纯py文件）
│   ├───cli（AetherPackBot CLI窗口）
│   ├───core（框架核心）
│   └───dashboard（对接webui）
│   └───api（对接所有api）
├───changelogs（更新版本log信息）
├───dashboard（webui面板前端）
├───data（默认不带，启动后自己创建并生成数据文件）
└───packages（自带插件）
    └───AetherPackBot（基础指令，功能）
```

## License

MIT License
