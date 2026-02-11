"""
默认配置 - 框架的所有默认配置值
Default configuration - all default configuration values of the framework.
"""

from __future__ import annotations

from typing import Any

# 框架版本
VERSION = "1.0.0"


def build_default_config() -> dict[str, Any]:
    """
    构建默认配置
    Build the default configuration.
    """
    return {
        # Web 服务配置
        "web": {
            "host": "0.0.0.0",
            "port": 9000,
            "username": "admin",
            "password": "",
            "enable_cors": True,
        },
        # 存储配置
        "store": {
            "db_path": "data/aether.db",
        },
        # 平台配置列表
        "platforms": [],
        # 平台通用设置
        "platform_settings": {
            "wake_prefix": [],
            "reply_prefix": "",
            "rate_limit_per_minute": 30,
            "whitelist": [],
            "blacklist": [],
            "content_safety_enabled": False,
            "blocked_words": [],
            "reply_with_at": True,
            "segment_reply": False,
            "segment_threshold": 400,
        },
        # 智能层（LLM）配置
        "providers": [],
        "provider_settings": {
            "enable_streaming": True,
            "context_limit": 20,
            "system_prompt": "",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        # STT 配置
        "stt": {
            "enabled": False,
            "provider": "",
        },
        # TTS 配置
        "tts": {
            "enabled": False,
            "provider": "",
        },
        # 扩展包配置
        "packs": {},
        # Agent 配置
        "agent": {
            "enabled": False,
            "runner_type": "tool_loop",
            "max_iterations": 10,
        },
        # 知识库配置
        "knowledge_base": {
            "enabled": False,
            "chunk_size": 512,
            "top_k": 5,
        },
        # 人格配置
        "persona": {
            "default": "",
        },
        # 日志配置
        "logging": {
            "level": "INFO",
            "file": "data/logs/aether.log",
        },
    }
