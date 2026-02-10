from AetherPackBot.core.plugin.Rfc import rfc
import uvicorn
import logging

from AetherPackBot.core.util.command_parser import CommandParserMixin


class Plugin(CommandParserMixin):
    """所有插件的父类"""

    author: str
    name: str

    async def initialize(self) -> None:
        """当插件被激活时会调用这个方法"""

    async def terminate(self) -> None:
        """当插件被禁用、重载插件时会调用这个方法"""

    def __del__(self) -> None:
        """[Deprecated] 当插件被禁用、重载插件时会调用这个方法"""

__all__ = ["Plugin"]

if __name__ == "__main__":
    rfc.post = 9191
    uvicorn.run(rfc, host="0.0.0.0", port=rfc.post)
    logging.info("RFC插件接口在端口${}启动".format(rfc))