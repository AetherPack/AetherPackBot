#!/usr/bin/env python3
"""
AetherPackBot - Multi-platform LLM Chatbot Framework
Main entry point for the application.
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def install_dependencies() -> None:
    """
    Smart dependency installer:
    - First run: install all from requirements.txt, then record installed set
    - Subsequent runs: only check for missing packages and install them
    """
    requirements_file = PROJECT_ROOT / "requirements.txt"
    marker_file = PROJECT_ROOT / "data" / ".deps_installed"

    if not requirements_file.exists():
        return

    def _parse_requirements() -> list[str]:
        """Parse package names from requirements.txt (ignore comments/blanks)."""
        pkgs = []
        for line in requirements_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Extract bare package name: "aiohttp>=3.11.0" -> "aiohttp"
            import re
            name = re.split(r"[>=<!\[;]", line)[0].strip().lower()
            if name:
                pkgs.append(name)
        return pkgs

    def _get_installed() -> set[str]:
        """Get set of currently installed package names."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=columns",
                 "--disable-pip-version-check"],
                capture_output=True, text=True, timeout=30,
            )
            installed = set()
            for line in result.stdout.splitlines()[2:]:  # skip header lines
                parts = line.split()
                if parts:
                    installed.add(parts[0].lower())
            return installed
        except Exception:
            return set()

    def _install(packages: list[str]) -> None:
        """Install a list of packages via pip."""
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

    # --- First run: full install from requirements.txt ---
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

        # Write marker
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.write_text(
            "\n".join(required), encoding="utf-8"
        )
        return

    # --- Subsequent runs: only install missing packages ---
    installed = _get_installed()
    # Normalize: pip uses hyphens, requirements may use underscores
    normalize = lambda s: s.replace("_", "-").lower()
    installed_norm = {normalize(p) for p in installed}

    missing = [pkg for pkg in required if normalize(pkg) not in installed_norm]

    if not missing:
        print("  [deps] All dependencies OK")
        return

    print(f"  [deps] Installing {len(missing)} missing: {', '.join(missing)}")
    _install(missing)

    # Update marker
    marker_file.write_text(
        "\n".join(required), encoding="utf-8"
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
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
    """Validate runtime environment requirements."""
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required.")
        sys.exit(1)


def display_banner() -> None:
    """Display application startup banner."""
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
    """Main application entry point."""
    from AetherPackBot.core.kernel import ApplicationKernel
    from AetherPackBot.core.logging import LogManager
    
    args = parse_arguments()
    check_environment()
    display_banner()
    
    # Initialize logging
    log_manager = LogManager()
    logger = log_manager.GetLogger("main")
    
    logger.info("Initializing AetherPackBot...")
    
    try:
        # Create and boot the application kernel
        kernel = ApplicationKernel(
            webui_dir=args.webui_dir,
            config_path=args.config,
            debug=args.debug,
        )
        
        await kernel.boot()
        logger.info("AetherPackBot started successfully.")
        
        # Run until shutdown signal
        await kernel.run_forever()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if "kernel" in locals():
            await kernel.shutdown()
        logger.info("AetherPackBot shutdown complete.")


if __name__ == "__main__":
    install_dependencies()
    asyncio.run(main())
