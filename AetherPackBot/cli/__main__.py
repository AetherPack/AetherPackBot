"""`python -m AetherPackBot.cli` 的命令行启动入口。"""

from AetherPackBot.cli.main import run_cli


def main() -> int:
    """执行 CLI 并返回进程退出码。"""
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
