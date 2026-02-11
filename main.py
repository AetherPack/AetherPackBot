"""
AetherPackBot 新入口
AetherPackBot new main entry.
"""

import asyncio
import mimetypes
import os
import sys
from pathlib import Path

# 将父目录添加到 sys.path / Add parent directory to sys.path
sys.path.append(Path(__file__).parent.as_posix())

LOGO = r"""
    ___         __  __                ____             __   ____        __
   /   |  ___  / /_/ /_  ___  _____/ __ \____ ______/ /__/ __ )____  / /_
  / /| | / _ \/ __/ __ \/ _ \/ ___/ /_/ / __ `/ ___/ //_/ __  / __ \/ __/
 / ___ |/  __/ /_/ / / /  __/ /  / ____/ /_/ / /__/ ,< / /_/ / /_/ / /_
/_/  |_|\___/\__/_/ /_/\___/_/  /_/    \__,_/\___/_/|_/_____/\____/\__/

"""

def check_env() -> None:
    """检查运行环境 / Check runtime environment."""
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 10):
        print("请使用 Python 3.10+ 运行本项目。")
        sys.exit(1)

    # 确保必要目录存在 / Ensure necessary directories exist
    os.makedirs("data/config", exist_ok=True)
    os.makedirs("data/packs", exist_ok=True)
    os.makedirs("data/temp", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    # 修复 MIME 类型 / Fix MIME types
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/javascript", ".mjs")
    mimetypes.add_type("application/json", ".json")


async def main() -> None:
    """主函数 / Main function."""
    from AetherPackBot.utils.logging import setup_logging

    setup_logging(log_file="data/logs/aether.log")

    import logging

    logger = logging.getLogger("AetherPackBot")

    from AetherPackBot import __app_name__, __version__

    logger.info("%s v%s 正在启动...", __app_name__, __version__)

    from AetherPackBot.kernel.bootstrap import Bootstrap

    bootstrap = Bootstrap()

    try:
        await bootstrap.start()
        await bootstrap.run_forever()
    except Exception:
        logger.exception("启动过程中发生致命错误")
    finally:
        await bootstrap.shutdown()


if __name__ == "__main__":
    check_env()
    print(LOGO)
    print("  AetherPackBot - Event-driven Microkernel Chat Framework\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown by user.")
