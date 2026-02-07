import asyncio
import uuid
import time
import base64
from typing import Any, cast

# 尝试导入 aiocqhttp，如果不存在则提示用户安装
try:
    from aiocqhttp import CQHttp, Event
    _AIOCQHTTP_AVAILABLE = True
except ImportError:
    _AIOCQHTTP_AVAILABLE = False
    CQHttp = None  # type: ignore
    Event = None   # type: ignore

from core.api.platforms import (
    BasePlatformAdapter,
    PlatformConfig,
    PlatformStatus,
    PlatformCapabilities,
)
from core.api.messages import (
    Message,
    MessageChain,
    MessageSession,
    PlatformMetadata,
    TextComponent,
    ImageComponent,
    ComponentType
)
from core.kernel.logging import get_logger

logger = get_logger("platforms.qq_onebot")

class QQOneBotAdapter(BasePlatformAdapter):
    """
    QQ (OneBot/CQHttp) 平台适配器。
    
    基于 aiocqhttp 实现，支持 OneBot V11 反向 WebSocket 连接。
    """
    
    def __init__(self, config: PlatformConfig) -> None:
        if not _AIOCQHTTP_AVAILABLE:
            raise ImportError("缺少依赖: aiocqhttp。请运行 `pip install aiocqhttp` 进行安装。")
        super().__init__(config)
        self._capabilities = PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_mentions=True,
        )
        
        # 从配置中获取 OneBot 连接参数（兼容多种字段名）
        s = self.config.settings
        self.host = s.get("host") or s.get("ws_reverse_host", "0.0.0.0")
        self.port = int(s.get("port") or s.get("ws_reverse_port", 8081))
        # token 可能在 credentials 中 (通过 config_schema 自动映射) 或 settings 中
        self.access_token = (
            self.config.credentials.get("token", "")
            or self.config.credentials.get("access_token", "")
            or s.get("token", "")
        )
        
        # 记录机器人自身 QQ 号，用于检测 @bot
        self._self_id: str = ""
        
        # 初始化 CQHttp Bot 对象
        # aiocqhttp 自动同时监听 HTTP 和反向 WebSocket，无需指定 use_ws_reverse
        self.bot = CQHttp(
            api_timeout_sec=120,
            access_token=self.access_token or None
        )
        
        # 注册事件处理器
        self._register_handlers()
        self._task: asyncio.Task | None = None

    def _register_handlers(self):
        """注册 OneBot 事件回调"""

        @self.bot.on_meta_event
        async def _on_meta(event: Event):
            """处理 OneBot 生命周期事件（连接/心跳等）"""
            if getattr(event, 'meta_event_type', '') == 'lifecycle':
                sub_type = getattr(event, 'sub_type', '')
                if sub_type == 'connect':
                    logger.info(f"OneBot 客户端已连接 [{self.platform_id}]")
                    self._set_status(PlatformStatus.CONNECTED)
                    # 参考 AstrBot：连接后获取机器人自身 QQ 号，用于 @bot 检测
                    try:
                        self._self_id = str(getattr(event, 'self_id', ''))
                        if not self._self_id:
                            info = await self.bot.get_login_info()
                            self._self_id = str(info.get('user_id', ''))
                        logger.info(f"机器人 QQ 号: {self._self_id}")
                    except Exception as e:
                        logger.warning(f"获取机器人 QQ 号失败: {e}")
                elif sub_type == 'disable':
                    logger.warning(f"OneBot 客户端已断开 [{self.platform_id}]")
                    self._set_status(PlatformStatus.DISCONNECTED)

        @self.bot.on_message
        async def _on_message(event: Event):
            """Convert OneBot event to internal Message and dispatch."""
            try:
                # 获取 self_id（如果还没拿到的话）
                if not self._self_id:
                    self._self_id = str(getattr(event, 'self_id', ''))
                
                user_id = str(event.user_id)
                group_id = str(event.group_id) if getattr(event, 'group_id', None) else ""
                is_group = bool(group_id)
                user_name = ""
                if hasattr(event, 'sender') and isinstance(event.sender, dict):
                    user_name = event.sender.get('nickname', '') or event.sender.get('card', '')

                session = MessageSession(
                    session_id=f"onebot:{group_id or user_id}",
                    platform_id=self.platform_id,
                    is_group=is_group,
                    group_id=group_id if is_group else None,
                    user_id=user_id,
                )

                # Build message chain from OneBot segments
                # 参考 AstrBot: convert_message() 解析各类消息段并检测 @bot
                chain = MessageChain()
                raw_msgs = event.message if isinstance(event.message, list) else []
                is_mentioned = False
                
                # Debug logging for potential issues
                at_segments = [s for s in raw_msgs if (isinstance(s, dict) and s.get('type') == 'at') or (hasattr(s, 'type') and s.type == 'at')]
                if at_segments:
                    logger.debug(f"[OneBot] Debug At: self_id={self._self_id}, segments={at_segments}")
                
                for seg in raw_msgs:
                    seg_type = seg.get('type', '') if isinstance(seg, dict) else getattr(seg, 'type', '')
                    seg_data = seg.get('data', {}) if isinstance(seg, dict) else getattr(seg, 'data', {})
                    
                    if seg_type == 'text':
                        chain.text(seg_data.get('text', ''))
                    elif seg_type == 'image':
                        chain.image(url=seg_data.get('url'), file_path=seg_data.get('file'))
                    elif seg_type == 'at':
                        # 参考 AstrBot: 检查 at 段的 qq 是否等于 self_id
                        at_qq = str(seg_data.get('qq', ''))
                        if at_qq == self._self_id or at_qq == 'all':
                            is_mentioned = True
                        chain.mention(user_id=at_qq)
                    elif seg_type == 'reply':
                        reply_msg_id = str(seg_data.get('id', ''))
                        chain.reply_to(reply_msg_id)
                    elif seg_type == 'face':
                        # 表情消息段，忽略或转为文字
                        pass

                msg = Message(
                    message_id=str(getattr(event, 'message_id', '') or uuid.uuid4().hex[:8]),
                    chain=chain,
                    session=session,
                    platform_meta=PlatformMetadata(
                        platform_name="QQ (OneBot)",
                        platform_id=self.platform_id,
                        adapter_type="qq_onebot",
                    ),
                    sender_id=user_id,
                    sender_name=user_name,
                    is_mentioned=is_mentioned,
                    raw_data=event,
                )
                logger.debug(f"[OneBot] {user_name}({user_id}): {chain.plain_text} [mentioned={is_mentioned}]")

                # Dispatch into processing pipeline (same as Telegram/Discord)
                if hasattr(self, '_platform_manager') and self._platform_manager:
                    await self._platform_manager.dispatch_message(msg)

            except Exception as e:
                logger.exception(f"处理 OneBot 消息失败: {e}")

    async def start(self) -> None:
        """启动 OneBot 服务（运行在后台 Task 中）"""
        self._set_status(PlatformStatus.CONNECTING)
        logger.info(f"正在启动 OneBot 服务，监听 {self.host}:{self.port}...")
        
        # 在后台任务中运行 aiocqhttp server
        # 注意：CQHttp.run_task 是一个阻塞的协程，会启动服务器
        self._task = asyncio.create_task(
            self.bot.run_task(host=self.host, port=self.port)
        )
        # 注意：status 将在 websocket 连接时更新为 CONNECTED

    async def stop(self) -> None:
        """停止服务"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._set_status(PlatformStatus.DISCONNECTED)
        logger.info("OneBot 服务已停止")

    async def send_message(
        self,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """发送消息实现"""
        if self.status != PlatformStatus.CONNECTED:
            logger.warning("尝试向未连接的 OneBot 平台发送消息")
        
        try:
            message_arr = self._convert_chain_to_onebot(chain)
            
            is_group = session.is_group
            
            if is_group and session.group_id:
                result = await self.bot.send_msg(
                    message_type="group",
                    group_id=int(session.group_id),
                    message=message_arr,
                )
            elif session.user_id:
                result = await self.bot.send_msg(
                    message_type="private",
                    user_id=int(session.user_id),
                    message=message_arr,
                )
            else:
                logger.error("send_message: no target (group_id/user_id)")
                return None
                
            msg_id = result.get("message_id", "") if isinstance(result, dict) else ""
            return str(msg_id) if msg_id else "sent"
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return None

    # --- 内部转换方法 ---

    def _convert_chain_to_onebot(self, chain: MessageChain) -> list[dict]:
        """将内部 MessageChain 转换为 OneBot 数组格式"""
        onebot_arr = []
        for comp in chain.components:
            if comp.type == ComponentType.TEXT:
                onebot_arr.append({
                    "type": "text",
                    "data": {"text": comp.data}
                })
            elif comp.type == ComponentType.IMAGE:
                img_comp = cast(ImageComponent, comp)
                data = {}
                if img_comp.file_path:
                    data["file"] = f"file:///{img_comp.file_path}"
                elif img_comp.url:
                    data["file"] = img_comp.url
                elif img_comp.base64_data:
                    data["file"] = f"base64://{img_comp.base64_data}"
                
                if data:
                    onebot_arr.append({
                        "type": "image",
                        "data": data
                    })
            elif comp.type == ComponentType.MENTION:
                # @某人
                from core.api.messages import MentionComponent
                mention_comp = cast(MentionComponent, comp)
                onebot_arr.append({
                    "type": "at",
                    "data": {"qq": mention_comp.user_id}
                })
            elif comp.type == ComponentType.REPLY:
                # 回复消息
                from core.api.messages import ReplyComponent
                reply_comp = cast(ReplyComponent, comp)
                onebot_arr.append({
                    "type": "reply",
                    "data": {"id": reply_comp.message_id}
                })
        return onebot_arr

