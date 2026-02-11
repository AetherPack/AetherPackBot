#!/usr/bin/env python3
"""
AetherPackBot - 多平台 LLM 聊天机器人框架
应用主入口。
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

# 确保项目根目录已加入 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def install_dependencies() -> None:
    """
    智能依赖安装器：
    - 首次运行：从 requirements.txt 完整安装并记录已安装集合
    - 后续运行：仅检查缺失依赖并安装
    """
    requirements_file = PROJECT_ROOT / "requirements.txt"
    marker_file = PROJECT_ROOT / "data" / ".deps_installed"

    if not requirements_file.exists():
        return

    def _parse_requirements() -> list[str]:
        """从 requirements.txt 解析包名（忽略注释和空行）。"""
        pkgs = []
        for line in requirements_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # 提取纯包名："aiohttp>=3.11.0" -> "aiohttp"
            import re
            name = re.split(r"[>=<!\[;]", line)[0].strip().lower()
            if name:
                pkgs.append(name)
        return pkgs

    def _get_installed() -> set[str]:
        """获取当前已安装包名集合。"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=columns",
                 "--disable-pip-version-check"],
                capture_output=True, text=True, timeout=30,
            )
            installed = set()
            for line in result.stdout.splitlines()[2:]:  # 跳过表头行
                parts = line.split()
                if parts:
                    installed.add(parts[0].lower())
            return installed
        except Exception:
            return set()

    def _install(packages: list[str]) -> None:
        """通过 pip 安装一组包。"""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "--quiet", "--disable-pip-version-check"] + packages,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            err_msg = (result.stderr or result.stdout or "").strip()
            for line in err_msg.splitlines()[-8:]:
                print(f"    {line}")
            print("  [deps] Some packages failed to install, continuing...")

    required = _parse_requirements()
    if not required:
        return

    # --- 首次运行：按 requirements.txt 全量安装 ---
    if not marker_file.exists():
        print("  [deps] First run - installing all dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "-r", str(requirements_file),
             "--quiet", "--disable-pip-version-check"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("  [deps] All dependencies installed OK")
        else:
            err_msg = (result.stderr or result.stdout or "").strip()
            for line in err_msg.splitlines()[-8:]:
                print(f"    {line}")
            print("  [deps] Some dependencies failed, continuing...")

        # 写入标记文件
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.write_text(
            "\n".join(required), encoding="utf-8"
        )
        return

    # --- 后续运行：仅安装缺失包 ---
    installed = _get_installed()
    # 归一化：pip 使用连字符，requirements 可能使用下划线
    normalize = lambda s: s.replace("_", "-").lower()
    installed_norm = {normalize(p) for p in installed}

    missing = [pkg for pkg in required if normalize(pkg) not in installed_norm]

    if not missing:
        print("  [deps] All dependencies OK")
        return

    print(f"  [deps] Installing {len(missing)} missing: {', '.join(missing)}")
    _install(missing)

    # 更新标记文件
    marker_file.write_text(
        "\n".join(required), encoding="utf-8"
    )


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="AetherPackBot",
        description="Multi-platform LLM chatbot and development framework",
    )
    parser.add_argument(
        "--webui-dir",
        type=str,
        help="Specify custom WebUI static files directory",
        default=None,
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )
    return parser.parse_args()


def check_environment() -> None:
    """校验运行环境要求。"""
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required.")
        sys.exit(1)


def display_banner() -> None:
    """显示应用启动横幅。"""
    banner = r"""
    ___       _   _               ____            _    ____        _   
   / _ \  ___| |_| |__   ___ _ __|  _ \ __ _  ___| | _| __ )  ___ | |_ 
  / /_\ \/ _ \ __| '_ \ / _ \ '__| |_) / _` |/ __| |/ /  _ \ / _ \| __|
 / /   \  __/ |_| | | |  __/ |  |  __/ (_| | (__|   <| |_) | (_) | |_ 
 \_|   |\___|\__|_| |_|\___|_|  |_|   \__,_|\___|_|\_\____/ \___/ \__|
    |_|                                                               
"""
    print(banner)
    print("  Version 1.0.0 | Multi-platform LLM Chatbot Framework")
    print("  ─" * 32)


async def main() -> None:
    """应用主入口。"""
    from AetherPackBot.core.app_kernel import ApplicationKernel
    from AetherPackBot.core.logging import LogManager
    
    args = parse_arguments()
    check_environment()
    display_banner()
    
    # 初始化日志
    log_manager = LogManager()
    logger = log_manager.GetLogger("main")
    
    logger.info("正在初始化 AetherPackBot...")
    
    try:
        # 创建并启动应用内核
        kernel = ApplicationKernel(
            webui_dir=args.webui_dir,
            config_path=args.config,
            debug=args.debug,
        )
        
        await kernel.boot()
        logger.info("AetherPackBot 已成功启动！")
        
        # 持续运行直到收到关闭信号
        await kernel.run_forever()
        
    except KeyboardInterrupt:
        logger.info("收到关闭信号...")
    except Exception as e:
        logger.exception(f"致命错误: {e}")
        sys.exit(1)
    finally:
        if "kernel" in locals():
            await kernel.shutdown()
        logger.info("AetherPackBot 已成功关闭。")


if __name__ == "__main__":
    install_dependencies()
    asyncio.run(main())
