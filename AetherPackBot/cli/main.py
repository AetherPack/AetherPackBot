"""
CLI 主入口 - 使用 Click 框架
CLI main entry - using Click framework.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import click


@click.group()
def cli() -> None:
    """AetherPackBot - 事件驱动微内核多平台聊天机器人框架"""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Web 服务监听地址")
@click.option("--port", default=6185, type=int, help="Web 服务端口")
@click.option("--data-dir", default="data", help="数据目录")
def run(host: str, port: int, data_dir: str) -> None:
    """启动 AetherPackBot / Start AetherPackBot."""
    from AetherPackBot.utils.logging import setup_logging

    setup_logging()

    logger = logging.getLogger("AetherPackBot")
    logger.info("正在启动 AetherPackBot...")

    # 确保数据目录
    os.makedirs(os.path.join(data_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "packs"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "temp"), exist_ok=True)

    from AetherPackBot.kernel.bootstrap import Bootstrap

    bootstrap = Bootstrap()

    async def main() -> None:
        await bootstrap.start()
        await bootstrap.run_forever()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    except Exception:
        logger.exception("致命错误")
        sys.exit(1)


@cli.command()
def init() -> None:
    """初始化配置 / Initialize configuration."""
    import json

    from AetherPackBot.config.defaults import build_default_config

    config_path = os.path.join("data", "config", "aether_config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    if os.path.exists(config_path):
        click.echo(f"配置文件已存在: {config_path}")
        if not click.confirm("是否覆盖?"):
            return

    config = build_default_config()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    click.echo(f"配置文件已创建: {config_path}")


@cli.command()
def version() -> None:
    """显示版本信息 / Show version info."""
    from AetherPackBot import __app_name__, __version__

    click.echo(f"{__app_name__} v{__version__}")


@cli.group()
def pack() -> None:
    """扩展包管理 / Pack management."""
    pass


@pack.command("list")
def pack_list() -> None:
    """列出已安装的扩展包 / List installed packs."""
    packs_dir = os.path.join("data", "packs")
    if not os.path.isdir(packs_dir):
        click.echo("没有找到扩展包目录")
        return

    entries = os.listdir(packs_dir)
    if not entries:
        click.echo("没有已安装的扩展包")
        return

    for entry in entries:
        if os.path.isdir(os.path.join(packs_dir, entry)):
            click.echo(f"  - {entry}")


@pack.command("install")
@click.argument("source")
def pack_install(source: str) -> None:
    """安装扩展包（从 Git URL 或本地路径） / Install a pack."""
    click.echo(f"正在安装扩展包: {source}")
    # 未来实现 git clone 或本地复制逻辑
    click.echo("安装功能尚未实现")


@cli.group()
def conf() -> None:
    """配置管理 / Configuration management."""
    pass


@conf.command("show")
@click.argument("key", required=False)
def conf_show(key: str | None) -> None:
    """显示配置 / Show configuration."""
    import json

    config_path = os.path.join("data", "config", "aether_config.json")
    if not os.path.exists(config_path):
        click.echo("配置文件不存在，请先运行 init")
        return

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    if key:
        keys = key.split(".")
        current = config
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                click.echo(f"键 '{key}' 不存在")
                return

        click.echo(json.dumps(current, ensure_ascii=False, indent=2))
    else:
        click.echo(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
