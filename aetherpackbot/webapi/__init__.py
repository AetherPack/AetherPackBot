"""
Web API Layer - REST API and WebSocket server.

Provides the web interface including:
- REST API for management
- WebSocket for real-time updates
- Static file serving for dashboard
"""

from aetherpackbot.webapi.server import WebServer

__all__ = [
    "WebServer",
]
