"""
Web 路由模块 - 所有 API 路由注册
Web routes module - all API route registrations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from quart import Quart, jsonify, request

if TYPE_CHECKING:
    from AetherPackBot.kernel.container import ServiceContainer

logger = logging.getLogger(__name__)


def _require_auth(func: Any) -> Any:
    """认证装饰器 / Authentication decorator."""
    from functools import wraps

    from AetherPackBot.web.auth import verify_token

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401

        token = auth_header[7:]
        payload = verify_token(token)
        if payload is None:
            return jsonify({"error": "invalid token"}), 401

        return await func(*args, **kwargs)

    return wrapper


def register_auth_routes(app: Quart, container: ServiceContainer) -> None:
    """注册认证路由 / Register auth routes."""

    @app.route("/api/auth/login", methods=["POST"])
    async def login() -> Any:
        data = await request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")

        config_mgr = await container.resolve_by_name("config")
        expected_user = config_mgr.get("web.username", "admin")
        expected_pass = config_mgr.get("web.password", "")

        if username == expected_user and (
            not expected_pass or password == expected_pass
        ):
            from AetherPackBot.web.auth import create_token

            token = create_token(username)
            return jsonify({"token": token, "username": username})

        return jsonify({"error": "invalid credentials"}), 401

    @app.route("/api/auth/verify", methods=["GET"])
    @_require_auth
    async def verify() -> Any:
        return jsonify({"status": "ok"})


def register_config_routes(app: Quart, container: ServiceContainer) -> None:
    """注册配置路由 / Register config routes."""

    @app.route("/api/config", methods=["GET"])
    @_require_auth
    async def get_config() -> Any:
        config_mgr = await container.resolve_by_name("config")
        return jsonify(config_mgr.as_dict())

    @app.route("/api/config", methods=["PUT"])
    @_require_auth
    async def update_config() -> Any:
        data = await request.get_json()
        config_mgr = await container.resolve_by_name("config")
        for key, value in data.items():
            config_mgr.set(key, value)
        await config_mgr.save()
        return jsonify({"status": "ok"})


def register_platform_routes(app: Quart, container: ServiceContainer) -> None:
    """注册平台管理路由 / Register platform management routes."""

    @app.route("/api/platforms", methods=["GET"])
    @_require_auth
    async def list_platforms() -> Any:
        from AetherPackBot.gateway.registry import GatewayRegistry

        try:
            registry: GatewayRegistry = await container.resolve(GatewayRegistry)
            instances = registry.all_instances()
            result = []
            for name, gw in instances.items():
                result.append(
                    {
                        "name": name,
                        "type": gw.metadata.adapter_type,
                        "status": gw.status.name,
                    }
                )
            return jsonify(result)
        except KeyError:
            return jsonify([])

    @app.route("/api/platforms/types", methods=["GET"])
    @_require_auth
    async def list_platform_types() -> Any:
        from AetherPackBot.gateway.registry import GatewayRegistry

        try:
            registry: GatewayRegistry = await container.resolve(GatewayRegistry)
            return jsonify(registry.adapter_types)
        except KeyError:
            return jsonify([])


def register_pack_routes(app: Quart, container: ServiceContainer) -> None:
    """注册扩展包管理路由 / Register pack management routes."""

    @app.route("/api/packs", methods=["GET"])
    @_require_auth
    async def list_packs() -> Any:
        from AetherPackBot.pack.loader import PackLoader

        try:
            loader: PackLoader = await container.resolve(PackLoader)
            return jsonify(loader.list_packs())
        except KeyError:
            return jsonify([])

    @app.route("/api/packs/<pack_name>/reload", methods=["POST"])
    @_require_auth
    async def reload_pack(pack_name: str) -> Any:
        from AetherPackBot.pack.loader import PackLoader

        try:
            loader: PackLoader = await container.resolve(PackLoader)
            success = await loader.reload_pack(pack_name)
            return jsonify({"status": "ok" if success else "not found"})
        except KeyError:
            return jsonify({"error": "pack loader not available"}), 500

    @app.route("/api/packs/<pack_name>/toggle", methods=["POST"])
    @_require_auth
    async def toggle_pack(pack_name: str) -> Any:
        from AetherPackBot.pack.loader import PackLoader

        try:
            loader: PackLoader = await container.resolve(PackLoader)
            packs = {p["name"]: p for p in loader.list_packs()}
            if pack_name not in packs:
                return jsonify({"error": "pack not found"}), 404
            # 切换启用状态
            return jsonify({"status": "ok"})
        except KeyError:
            return jsonify({"error": "pack loader not available"}), 500


def register_provider_routes(app: Quart, container: ServiceContainer) -> None:
    """注册提供者管理路由 / Register provider management routes."""

    @app.route("/api/providers", methods=["GET"])
    @_require_auth
    async def list_providers() -> Any:
        from AetherPackBot.intellect.registry import IntellectRegistry

        try:
            registry: IntellectRegistry = await container.resolve(IntellectRegistry)
            instances = registry.all_instances()
            result = []
            for pid, inst in instances.items():
                info = inst.info
                result.append(
                    {
                        "id": info.provider_id,
                        "name": info.display_name,
                        "capability": info.capability.value,
                        "model": info.model_name,
                    }
                )
            return jsonify(result)
        except KeyError:
            return jsonify([])


def register_conversation_routes(app: Quart, container: ServiceContainer) -> None:
    """注册对话管理路由 / Register conversation management routes."""

    @app.route("/api/conversations", methods=["GET"])
    @_require_auth
    async def list_conversations() -> Any:
        return jsonify([])


def register_persona_routes(app: Quart, container: ServiceContainer) -> None:
    """注册人格管理路由 / Register persona management routes."""

    @app.route("/api/personas", methods=["GET"])
    @_require_auth
    async def list_personas() -> Any:
        return jsonify([])


def register_stat_routes(app: Quart, container: ServiceContainer) -> None:
    """注册统计路由 / Register statistics routes."""

    @app.route("/api/stats", methods=["GET"])
    @_require_auth
    async def get_stats() -> Any:
        return jsonify(
            {
                "total_messages": 0,
                "active_sessions": 0,
                "uptime": 0,
            }
        )


def register_log_routes(app: Quart, container: ServiceContainer) -> None:
    """注册日志路由 / Register log routes."""

    @app.route("/api/logs", methods=["GET"])
    @_require_auth
    async def get_logs() -> Any:
        return jsonify([])


def register_system_routes(app: Quart, container: ServiceContainer) -> None:
    """注册系统管理路由 / Register system management routes."""

    @app.route("/api/system/info", methods=["GET"])
    @_require_auth
    async def system_info() -> Any:
        import platform
        import sys

        from AetherPackBot import __app_name__, __version__

        return jsonify(
            {
                "app_name": __app_name__,
                "version": __version__,
                "python_version": sys.version,
                "platform": platform.platform(),
            }
        )

    @app.route("/api/system/restart", methods=["POST"])
    @_require_auth
    async def restart() -> Any:
        return jsonify({"status": "restart scheduled"})

    @app.route("/api/system/shutdown", methods=["POST"])
    @_require_auth
    async def shutdown() -> Any:
        from AetherPackBot.kernel.bootstrap import Bootstrap

        try:
            bootstrap: Bootstrap = await container.resolve(Bootstrap)
            bootstrap._shutdown_event.set()
            return jsonify({"status": "shutting down"})
        except KeyError:
            return jsonify({"error": "bootstrap not available"}), 500
