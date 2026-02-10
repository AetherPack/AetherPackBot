"""
Web Server - Quart-based async web server.

Provides REST API endpoints and serves the dashboard static files.
Supports full CRUD for providers, platforms, plugins, conversations.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, TYPE_CHECKING

import jwt
from quart import Quart, jsonify, request, send_from_directory, Response
from quart_cors import cors

from AetherPackBot.core.logging import get_logger

if TYPE_CHECKING:
    from AetherPackBot.core.container import ServiceContainer

logger = get_logger("webapi")


def _ok(data: Any = None, message: str = "ok") -> tuple:
    """Return a success response.

    Dict data is spread at the top level for backward compatibility with
    frontends that access ``response.data.token`` etc. directly, while the
    ``data`` key is always present for new frontends that use ``unwrap()``.
    """
    resp: dict[str, Any] = {"status": "ok", "message": message}
    if isinstance(data, dict):
        resp.update(data)          # spread fields at top level
    resp["data"] = data             # keep envelope for unwrap()
    return jsonify(resp), 200


def _error(message: str, code: int = 400) -> tuple:
    return jsonify({"status": "error", "message": message, "data": None}), code


class WebServer:
    """
    Async web server providing REST API for full management.
    """

    def __init__(
        self,
        container: "ServiceContainer",
        webui_dir: str | None = None,
    ) -> None:
        self._container = container
        self._webui_dir = webui_dir
        self._app: Quart | None = None
        self._server_task: asyncio.Task | None = None
        self._jwt_secret = secrets.token_hex(32)
        self._admin_username = "aetherpackbot"
        self._admin_password = "aetherpackbot"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        from AetherPackBot.core.storage.config import ConfigurationManager
        try:
            cm = await self._container.resolve(ConfigurationManager)
            wc = cm.web
            self._admin_username = wc.admin_username
            self._admin_password = wc.admin_password
            if wc.jwt_secret:
                self._jwt_secret = wc.jwt_secret
            host, port = wc.host, wc.port
        except Exception:
            host, port = "0.0.0.0", 8080

        self._app = Quart(__name__, static_folder=None)
        self._app = cors(
            self._app,
            allow_origin="*",
            allow_headers=["Content-Type", "Authorization"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )
        self._register_routes()
        self._server_task = asyncio.create_task(
            self._app.run_task(host=host, port=port)
        )
        logger.info(f"Web server started on http://{host}:{port}")

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        logger.info("Web server stopped")

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------

    def _create_token(self, username: str) -> str:
        return jwt.encode(
            {"sub": username, "iat": int(time.time()), "exp": int(time.time()) + 86400 * 7},
            self._jwt_secret,
            algorithm="HS256",
        )

    def _verify_token(self, token: str) -> bool:
        if not token:
            return False
        try:
            jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
            return True
        except jwt.PyJWTError:
            return False

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    def _register_routes(self) -> None:  # noqa: C901
        app = self._app
        if not app:
            return

        def require_auth(f):
            @wraps(f)
            async def decorated(*args, **kwargs):
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
                if not self._verify_token(token):
                    return _error("Unauthorized", 401)
                return await f(*args, **kwargs)
            return decorated

        # ===== HEALTH =====
        @app.route("/health")
        async def health():
            return jsonify({"status": "ok", "version": "1.0.0"})

        # ===== AUTH =====
        @app.route("/api/auth/login", methods=["POST"])
        async def login():
            try:
                data = await request.get_json()
            except Exception:
                return _error("Invalid request body", 400)
            if not data:
                return _error("Request body must be JSON", 400)
            username = data.get("username", "")
            password = data.get("password", "")
            if username == self._admin_username and password == self._admin_password:
                token = self._create_token(username)
                return _ok({"token": token, "username": username})
            return _error("Invalid credentials", 401)

        @app.route("/api/auth/verify", methods=["GET"])
        @require_auth
        async def verify():
            return _ok({"valid": True})

        # ===== STATUS =====
        @app.route("/api/status")
        @require_auth
        async def get_status():
            from AetherPackBot.core.platform.manager import PlatformManager
            from AetherPackBot.core.provider.manager import ProviderManager
            from AetherPackBot.core.plugin.manager import PluginManager
            import psutil

            result: dict[str, Any] = {
                "platforms": [],
                "providers": [],
                "plugins": [],
                "version": "1.0.0",
                "uptime": 0,
                "cpu_percent": 0,
                "memory_mb": 0,
            }

            try:
                proc = psutil.Process()
                result["cpu_percent"] = proc.cpu_percent(interval=0.1)
                result["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
                result["uptime"] = int(time.time() - proc.create_time())
            except Exception:
                pass

            try:
                pm = await self._container.resolve(PlatformManager)
                result["platforms"] = pm.get_status_list()
            except Exception:
                pass
            try:
                prov = await self._container.resolve(ProviderManager)
                result["providers"] = prov.get_status_list()
            except Exception:
                pass
            try:
                plm = await self._container.resolve(PluginManager)
                result["plugins"] = [
                    {"name": p.name, "version": p.metadata.version, "status": p.status.name}
                    for p in plm.get_all_plugins()
                ]
            except Exception:
                pass

            return _ok(result)

        # ===== CONFIG =====
        @app.route("/api/config", methods=["GET"])
        @require_auth
        async def get_config():
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                cm = await self._container.resolve(ConfigurationManager)
                cfg = cm.to_dict()
                if "web" in cfg:
                    cfg["web"]["admin_password"] = "******"
                    cfg["web"]["jwt_secret"] = "******"
                for p in cfg.get("providers", []):
                    if "api_key" in p:
                        k = p["api_key"]
                        p["api_key"] = k[:8] + "***" if len(k) > 8 else "***"
                return _ok(cfg)
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/config", methods=["PUT"])
        @require_auth
        async def update_config():
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                cm = await self._container.resolve(ConfigurationManager)
                data = await request.get_json()

                def _deep_merge(base: dict, patch: dict) -> dict:
                    """Recursively merge *patch* into *base* (mutates base)."""
                    for k, v in patch.items():
                        if isinstance(v, dict) and isinstance(base.get(k), dict):
                            _deep_merge(base[k], v)
                        else:
                            base[k] = v
                    return base

                for key, value in data.items():
                    if isinstance(value, dict):
                        existing = cm.get(key, {})
                        if isinstance(existing, dict):
                            value = _deep_merge(existing, value)
                    cm.set(key, value)
                await cm.save()
                return _ok(message="配置已保存")
            except Exception as e:
                return _error(str(e), 500)

        # ===== PROVIDERS CRUD =====
        @app.route("/api/providers", methods=["GET"])
        @require_auth
        async def list_providers():
            from AetherPackBot.core.provider.manager import ProviderManager
            try:
                prov = await self._container.resolve(ProviderManager)
                return _ok(prov.get_status_list())
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/providers", methods=["POST"])
        @require_auth
        async def add_provider():
            from AetherPackBot.core.provider.manager import ProviderManager, PROVIDER_TYPE_INFO
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                data = await request.get_json()
                ptype = data.get("type", "")
                type_info = PROVIDER_TYPE_INFO.get(ptype, {})
                requires_key = type_info.get("requires_api_key", True)
                if not ptype:
                    return _error("需要 type 字段")
                if requires_key and not data.get("api_key"):
                    return _error("需要 api_key 字段")
                # Auto-fill default model and api_base if not provided
                if not data.get("model") and type_info.get("default_model"):
                    data["model"] = type_info["default_model"]
                if not data.get("api_base_url") and type_info.get("default_api_base"):
                    data["api_base_url"] = type_info["default_api_base"]
                data.setdefault("name", ptype)
                
                # Validate provider can be instantiated before saving
                try:
                    prov = await self._container.resolve(ProviderManager)
                    provider = await prov.register_from_config(data)
                except ImportError as ie:
                    pkg = str(ie).replace("No module named ", "").strip("'\"")
                    return _error(f"缺少依赖包 {pkg}，请运行: pip install {pkg}", 500)
                except Exception as reg_err:
                    return _error(f"创建提供者失败: {reg_err}", 400)
                
                # Ensure ID is saved to config
                data["id"] = provider.provider_id
                
                cm = await self._container.resolve(ConfigurationManager)
                pl = cm.get("providers", [])
                pl.append(data)
                cm.set("providers", pl)
                await cm.save()
                return _ok({"id": provider.provider_id, "model": provider.model}, "提供者已添加")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/providers/<provider_id>", methods=["PUT"])
        @require_auth
        async def update_provider(provider_id: str):
            from AetherPackBot.core.provider.manager import ProviderManager
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                data = await request.get_json()
                prov = await self._container.resolve(ProviderManager)

                # Merge with existing config so empty fields keep old values
                old_config = prov.get_provider_config(provider_id)
                if old_config:
                    for key in ("api_key", "api_base_url", "model", "type", "name", "extra"):
                        if not data.get(key) and old_config.get(key):
                            data[key] = old_config[key]

                prov.unregister(provider_id)
                data.setdefault("id", provider_id)
                data.setdefault("name", data.get("type", "openai"))
                provider = await prov.register_from_config(data)

                # Handle is_default flag
                if data.get("is_default"):
                    prov.set_default(provider.provider_id)

                cm = await self._container.resolve(ConfigurationManager)
                pl = [p for p in cm.get("providers", []) if p.get("id") != provider_id]
                pl.append(data)
                cm.set("providers", pl)
                await cm.save()
                return _ok({"id": provider.provider_id}, "提供者已更新")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/providers/<provider_id>", methods=["DELETE"])
        @require_auth
        async def delete_provider(provider_id: str):
            from AetherPackBot.core.provider.manager import ProviderManager
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                prov = await self._container.resolve(ProviderManager)
                prov.unregister(provider_id)
                cm = await self._container.resolve(ConfigurationManager)
                pl = [p for p in cm.get("providers", []) if p.get("id") != provider_id]
                cm.set("providers", pl)
                await cm.save()
                return _ok(message="提供者已删除")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/providers/types", methods=["GET"])
        @require_auth
        async def list_provider_types():
            from AetherPackBot.core.provider.manager import PROVIDER_REGISTRY, PROVIDER_TYPE_INFO
            result = []
            for k in PROVIDER_REGISTRY:
                info = PROVIDER_TYPE_INFO.get(k, {})
                result.append({
                    "type": k,
                    "name": info.get("name", k.title()),
                    "description": info.get("description", ""),
                    "requires_api_key": info.get("requires_api_key", True),
                    "default_model": info.get("default_model", ""),
                    "models": info.get("models", []),
                    "default_api_base": info.get("default_api_base", ""),
                })
            return _ok(result)

        @app.route("/api/providers/<provider_id>/default", methods=["POST"])
        @require_auth
        async def set_default_provider(provider_id: str):
            from AetherPackBot.core.provider.manager import ProviderManager
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                prov = await self._container.resolve(ProviderManager)
                prov.set_default(provider_id)
                cm = await self._container.resolve(ConfigurationManager)
                cm.set("agent.default_provider", provider_id)
                await cm.save()
                return _ok(message="已设为默认提供者")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/providers/<provider_id>/health", methods=["GET"])
        @require_auth
        async def check_provider_health(provider_id: str):
            from AetherPackBot.core.provider.manager import ProviderManager
            try:
                prov = await self._container.resolve(ProviderManager)
                provider = prov.get(provider_id)
                if not provider:
                    return _error("提供者不存在", 404)
                healthy = await provider.health_check()
                return _ok({"healthy": healthy, "id": provider_id})
            except Exception as e:
                return _error(str(e), 500)

        # ===== PLATFORMS CRUD =====
        @app.route("/api/platforms", methods=["GET"])
        @require_auth
        async def list_platforms():
            from AetherPackBot.core.platform.manager import PlatformManager
            try:
                pm = await self._container.resolve(PlatformManager)
                return _ok(pm.get_status_list())
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/platforms", methods=["POST"])
        @require_auth
        async def add_platform():
            from AetherPackBot.core.platform.manager import PlatformManager
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                data = await request.get_json()
                if not data.get("type"):
                    return _error("需要 type 字段")
                pm = await self._container.resolve(PlatformManager)
                adapter = await pm.register_from_config(data)
                
                # Ensure ID is saved to config
                data["id"] = adapter.platform_id
                
                await pm._start_adapter(adapter)
                cm = await self._container.resolve(ConfigurationManager)
                pl = cm.get("platforms", [])
                pl.append(data)
                cm.set("platforms", pl)
                await cm.save()
                return _ok({"id": adapter.platform_id}, "平台已添加")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/platforms/<platform_id>", methods=["GET"])
        @require_auth
        async def get_platform(platform_id: str):
            """Get saved config for a single platform (for edit form)."""
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                cm = await self._container.resolve(ConfigurationManager)
                platforms = cm.get("platforms", [])
                for p in platforms:
                    if p.get("id") == platform_id:
                        return _ok(p)
                return _error("平台不存在", 404)
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/platforms/<platform_id>", methods=["PUT"])
        @require_auth
        async def update_platform(platform_id: str):
            from AetherPackBot.core.platform.manager import PlatformManager
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                data = await request.get_json()
                pm = await self._container.resolve(PlatformManager)
                old = pm.get_adapter(platform_id)
                if old:
                    try:
                        await old.stop()
                    except Exception:
                        pass
                pm.unregister(platform_id)
                data.setdefault("id", platform_id)
                adapter = await pm.register_from_config(data)
                await pm._start_adapter(adapter)
                cm = await self._container.resolve(ConfigurationManager)
                pl = [p for p in cm.get("platforms", []) if p.get("id") != platform_id]
                pl.append(data)
                cm.set("platforms", pl)
                await cm.save()
                return _ok({"id": adapter.platform_id}, "平台已更新")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/platforms/<platform_id>", methods=["DELETE"])
        @require_auth
        async def delete_platform(platform_id: str):
            from AetherPackBot.core.platform.manager import PlatformManager
            from AetherPackBot.core.storage.config import ConfigurationManager
            try:
                pm = await self._container.resolve(PlatformManager)
                adapter = pm.get_adapter(platform_id)
                if adapter:
                    try:
                        await adapter.stop()
                    except Exception:
                        pass
                pm.unregister(platform_id)
                cm = await self._container.resolve(ConfigurationManager)
                pl = [p for p in cm.get("platforms", []) if p.get("id") != platform_id]
                cm.set("platforms", pl)
                await cm.save()
                return _ok(message="平台已删除")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/platforms/<platform_id>/toggle", methods=["POST"])
        @require_auth
        async def toggle_platform(platform_id: str):
            from AetherPackBot.core.platform.manager import PlatformManager
            from AetherPackBot.core.api.platforms import PlatformStatus
            try:
                pm = await self._container.resolve(PlatformManager)
                adapter = pm.get_adapter(platform_id)
                if not adapter:
                    return _error("平台不存在", 404)
                if adapter.status == PlatformStatus.CONNECTED:
                    await adapter.stop()
                    return _ok({"status": "stopped", "enabled": False}, "平台已停止")
                else:
                    await pm._start_adapter(adapter)
                    return _ok({"status": "running", "enabled": True}, "平台已启动")
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/platforms/types", methods=["GET"])
        @require_auth
        async def list_platform_types():
            from AetherPackBot.core.platform.manager import PLATFORM_REGISTRY
            return _ok([
                {
                    "type": k,
                    "name": info.display_name,
                    "description": info.description,
                    "config_schema": info.config_schema,
                }
                for k, info in PLATFORM_REGISTRY.items()
            ])

        # ===== PLUGINS =====
        @app.route("/api/plugins", methods=["GET"])
        @require_auth
        async def list_plugins():
            from AetherPackBot.core.plugin.manager import PluginManager
            try:
                plm = await self._container.resolve(PluginManager)
                return _ok([
                    {
                        "name": p.name,
                        "version": p.metadata.version,
                        "author": p.metadata.author,
                        "description": p.metadata.description,
                        "status": p.status.name,
                        "is_builtin": p.is_builtin,
                    }
                    for p in plm.get_all_plugins()
                ])
            except Exception as e:
                return _error(str(e), 500)

        @app.route("/api/plugins/<plugin_name>/reload", methods=["POST"])
        @require_auth
        async def reload_plugin(plugin_name: str):
            from AetherPackBot.core.plugin.manager import PluginManager
            try:
                plm = await self._container.resolve(PluginManager)
                ok = await plm.reload_plugin(plugin_name)
                return _ok(message="插件已重载") if ok else _error("插件不存在", 404)
            except Exception as e:
                return _error(str(e), 500)

        # ===== TOOLS =====
        @app.route("/api/tools", methods=["GET"])
        @require_auth
        async def list_tools():
            from AetherPackBot.core.agent.orchestrator import AgentOrchestrator
            try:
                orch = await self._container.resolve(AgentOrchestrator)
                return _ok([
                    {
                        "name": t.name,
                        "description": t.description,
                        "enabled": t.enabled,
                        "parameters": [
                            {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                            for p in t.parameters
                        ],
                    }
                    for t in orch.get_all_tools()
                ])
            except Exception as e:
                return _error(str(e), 500)

        # ===== CHAT =====
        @app.route("/api/chat", methods=["POST"])
        @require_auth
        async def chat():
            from AetherPackBot.core.provider.manager import ProviderManager
            from AetherPackBot.core.api.providers import LLMMessage, LLMRequest
            from AetherPackBot.core.storage.database import DatabaseManager, MessageHistoryModel
            try:
                data = await request.get_json()
                user_msg = data.get("message", "")
                if not user_msg:
                    return _error("消息不能为空")

                prov_mgr = await self._container.resolve(ProviderManager)
                provider = (
                    prov_mgr.get(data.get("provider_id"))
                    if data.get("provider_id")
                    else prov_mgr.get_default()
                )
                if not provider:
                    return _error("没有可用的 LLM 提供者，请先在设置中添加")

                messages = []
                sp = data.get("system_prompt", "")
                
                # 如果前端没传 system_prompt，自动从配置中加载人格设置
                if not sp:
                    from AetherPackBot.core.storage.config import ConfigurationManager
                    try:
                        cm = await self._container.resolve(ConfigurationManager)
                        # 先尝试顶层 system_prompt（前端设置可能写在这里）
                        sp = cm.get("system_prompt", "")
                        if not sp:
                            # 再尝试从 personas 加载
                            personas = cm.get("personas", [])
                            default_name = cm.get("default_persona", "")
                            if personas:
                                persona = None
                                if default_name:
                                    persona = next((p for p in personas if p.get("name") == default_name), None)
                                if not persona:
                                    persona = personas[0]
                                sp = persona.get("prompt", "") or persona.get("system_prompt", "") or persona.get("content", "")
                    except Exception:
                        pass
                
                if sp:
                    messages.append(LLMMessage(role="system", content=sp))
                for h in data.get("history", []):
                    messages.append(LLMMessage(role=h["role"], content=h["content"]))
                messages.append(LLMMessage(role="user", content=user_msg))

                # Save user message
                db = await self._container.resolve(DatabaseManager)
                async with db.session() as session:
                    # Use ID 0 for web console chat
                    session.add(MessageHistoryModel(
                        conversation_id=0,
                        role="user",
                        content=user_msg
                    ))
                    await session.commit()

                resp = await provider.chat(LLMRequest(
                    messages=messages,
                    model=data.get("model"),
                    temperature=data.get("temperature", 0.7),
                    max_tokens=data.get("max_tokens"),
                ))

                # Save assistant message
                async with db.session() as session:
                    session.add(MessageHistoryModel(
                        conversation_id=0,
                        role="assistant",
                        content=resp.content
                    ))
                    await session.commit()

                return _ok({
                    "content": resp.content,
                    "model": resp.model,
                    "usage": resp.usage,
                    "finish_reason": resp.finish_reason,
                })
            except Exception as e:
                logger.exception(f"Chat error: {e}")
                return _error(str(e), 500)

        @app.route("/api/conversations", methods=["GET"])
        @require_auth
        async def list_conversations():
            from AetherPackBot.core.storage.database import DatabaseManager
            try:
                db = await self._container.resolve(DatabaseManager)
                convs = await db.get_recent_conversations(limit=50)
                return _ok([
                    {
                        "id": c.id,
                        "platform": c.platform_id,
                        "user_id": c.user_id,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                    }
                    for c in convs
                ])
            except Exception as e:
                return _error(str(e), 500)

        # ===== CHAT =====
        @app.route("/api/chat/history", methods=["GET"])
        @require_auth
        async def get_chat_history():
            from AetherPackBot.core.storage.database import DatabaseManager, MessageHistoryModel
            from sqlalchemy import select
            try:
                db = await self._container.resolve(DatabaseManager)
                limit = request.args.get("limit", 50, type=int)
                async with db.session() as session:
                    stmt = select(MessageHistoryModel).order_by(MessageHistoryModel.created_at.desc()).limit(limit)
                    result = await session.execute(stmt)
                    history = result.scalars().all()
                    return _ok({
                        "history": [
                            {
                                "role": h.role,
                                "content": h.content,
                                "time": h.created_at.isoformat()
                            } for h in reversed(history)
                        ]
                    })
            except Exception as e:
                return _error(str(e), 500)

        # ===== LOGS =====
        @app.route("/api/logs", methods=["GET"])
        @require_auth
        async def get_logs():
            from AetherPackBot.core.logging import get_log_broker
            try:
                count = request.args.get("count", 100, type=int)
                broker = get_log_broker()
                logs = broker.get_recent(count)
                
                result = []
                for l in logs:
                    ts = l.get("time", 0)
                    try:
                        ts_str = datetime.fromtimestamp(ts).isoformat()
                    except Exception:
                        ts_str = str(ts)
                        
                    result.append({
                        "timestamp": ts_str,
                        "level": l.get("level", "INFO"),
                        "logger": l.get("logger", "root"),
                        "message": l.get("data", ""),
                    })
                    
                return _ok(result)
            except Exception as e:
                return _error(str(e), 500)

        # ===== STATIC FILES =====
        @app.route("/")
        @app.route("/<path:path>")
        async def serve_static(path: str = "index.html"):
            if path.startswith("api/"):
                return _error("Not found", 404)
            static_dir = self._get_static_dir()
            if not static_dir:
                return Response(self._get_fallback_html(), content_type="text/html; charset=utf-8")
            fp = static_dir / path
            if fp.is_file():
                return await send_from_directory(str(static_dir), path)
            if (static_dir / "index.html").exists():
                return await send_from_directory(str(static_dir), "index.html")
            return _error("Not found", 404)

    def _get_static_dir(self) -> Path | None:
        from AetherPackBot.core.paths import get_dashboard_dir

        # 优先使用自定义路径（如果在构造时传入）
        if self._webui_dir:
            p = Path(self._webui_dir)
            if p.exists():
                return p

        # 统一使用 data/dist（对标 AstrBot）
        dist = get_dashboard_dir()
        if dist.exists():
            return dist

        # 兼容旧的 dashboard/dist 构建产物
        fallback = Path("dashboard/dist")
        if fallback.exists():
            return fallback

        return None

    def _get_fallback_html(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AetherPackBot</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:linear-gradient(135deg,#1e3a8a,#3b82f6);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:#fff;border-radius:16px;padding:40px;max-width:500px;width:100%;box-shadow:0 25px 50px -12px rgba(0,0,0,.25)}.logo{width:64px;height:64px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 24px}.logo span{color:#fff;font-size:32px;font-weight:bold}h1{text-align:center;color:#1f2937;margin-bottom:8px}.sub{text-align:center;color:#6b7280;margin-bottom:32px}.st{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:16px;margin-bottom:24px}.st-t{color:#065f46;font-weight:600;display:flex;align-items:center;gap:8px}.st-t::before{content:'';width:8px;height:8px;background:#10b981;border-radius:50%}.info{background:#f3f4f6;border-radius:8px;padding:16px}.info p{color:#4b5563;font-size:14px;line-height:1.6}.code{background:#1f2937;color:#10b981;padding:12px 16px;border-radius:6px;font-family:monospace;font-size:13px;margin-top:12px}</style>
</head><body><div class="card"><div class="logo"><span>A</span></div><h1>AetherPackBot</h1><p class="sub">v1.0.0 - LLM Chatbot Framework</p><div class="st"><div class="st-t">服务运行中</div></div><div class="info"><p>Dashboard 尚未构建。请运行以下命令：</p><div class="code">cd dashboard && npm install && npm run build</div></div></div></body></html>"""
