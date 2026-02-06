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
aetherpackbot/
├── kernel/          # Core kernel (lifecycle, container, events)
├── protocols/       # Abstract protocols and interfaces
├── messaging/       # Message handling and processing
├── platforms/       # Platform adapters (Telegram, Discord, etc.)
├── providers/       # LLM provider implementations
├── plugins/         # Plugin system
├── agents/          # Agent system with tool calling
├── storage/         # Database and persistence
├── webapi/          # REST API and WebSocket server
├── cli/             # Command-line interface
└── extensions/      # Built-in extensions
```

## License

MIT License
