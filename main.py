#!/usr/bin/env python3
"""
AetherPackBot - Multi-platform LLM Chatbot Framework
Main entry point for the application.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))


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
    from aetherpackbot.kernel import ApplicationKernel
    from aetherpackbot.kernel.logging import LogManager
    
    args = parse_arguments()
    check_environment()
    display_banner()
    
    # Initialize logging
    log_manager = LogManager()
    logger = log_manager.get_logger("main")
    
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
    asyncio.run(main())
