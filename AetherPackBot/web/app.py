"""
Web 应用 - 基于 Quart 的 API 和管理面板服务
Web application - Quart-based API and dashboard service.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from quart import Quart, jsonify, send_from_directory

if TYPE_CHECKING:
    from AetherPackBot.kernel.container import ServiceContainer

logger = logging.getLogger(__name__)


class WebApplication:
    """
    Web 应用 - 提供 REST API 和静态文件服务
    Web application - provides REST API and static file serving.
    """

    def __init__(
        self,
        container: ServiceContainer,
        host: str = "0.0.0.0",
        port: int = 9000,
    ) -> None:
        self._container = container
        self._host = host
        self._port = port
        self._app = Quart(__name__)
        self._setup_routes()

    def _setup_routes(self) -> None:
        """设置路由 / Setup routes."""
        from AetherPackBot.web.routes import (
            register_auth_routes,
            register_config_routes,
            register_conversation_routes,
            register_log_routes,
            register_pack_routes,
            register_persona_routes,
            register_platform_routes,
            register_provider_routes,
            register_stat_routes,
            register_system_routes,
        )

        register_auth_routes(self._app, self._container)
        register_config_routes(self._app, self._container)
        register_platform_routes(self._app, self._container)
        register_pack_routes(self._app, self._container)
        register_provider_routes(self._app, self._container)
        register_conversation_routes(self._app, self._container)
        register_persona_routes(self._app, self._container)
        register_stat_routes(self._app, self._container)
        register_log_routes(self._app, self._container)
        register_system_routes(self._app, self._container)

        # 静态文件
        @self._app.route("/")
        async def index() -> Any:
            dist_dir = os.path.join("data", "dist")
            if os.path.exists(os.path.join(dist_dir, "index.html")):
                return await send_from_directory(dist_dir, "index.html")
            return jsonify({"message": "AetherPackBot API", "status": "running"})

        @self._app.route("/<path:path>")
        async def static_files(path: str) -> Any:
            dist_dir = os.path.join("data", "dist")
            file_path = os.path.join(dist_dir, path)
            if os.path.exists(file_path):
                return await send_from_directory(dist_dir, path)
            return jsonify({"error": "not found"}), 404

    async def run(self) -> None:
        """启动服务器 / Start server."""
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"{self._host}:{self._port}"]
        config.accesslog = None

        logger.info("Web 服务运行在 http://%s:%d", self._host, self._port)

        try:
            await serve(self._app, config)
        except Exception:
            logger.exception("Web 服务出错")
