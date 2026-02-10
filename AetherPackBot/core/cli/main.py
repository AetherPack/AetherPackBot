"""
CLI Main - Command-line interface entry point.

Provides interactive commands for bot management and development tools.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from AetherPackBot.core.kernel.logging import get_logger

logger = get_logger("cli")


def run_cli() -> int:
    """
    Main entry point for CLI.
    
    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = argparse.ArgumentParser(
        prog="aetherpackbot",
        description="AetherPackBot CLI - LLM Chatbot Framework",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Start the bot")
    run_parser.add_argument(
        "-c", "--config",
        help="Path to config file",
        default="data/config/config.json",
    )
    run_parser.add_argument(
        "-d", "--data-dir",
        help="Data directory path",
        default="data",
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    
    # Plugin commands
    plugin_parser = subparsers.add_parser("plugin", help="Plugin management")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_command")
    
    plugin_list = plugin_sub.add_parser("list", help="List installed plugins")
    plugin_install = plugin_sub.add_parser("install", help="Install a plugin")
    plugin_install.add_argument("source", help="Plugin source (path or URL)")
    plugin_uninstall = plugin_sub.add_parser("uninstall", help="Uninstall a plugin")
    plugin_uninstall.add_argument("name", help="Plugin name")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_sub = config_parser.add_subparsers(dest="config_command")
    
    config_show = config_sub.add_parser("show", help="Show current config")
    config_set = config_sub.add_parser("set", help="Set a config value")
    config_set.add_argument("key", help="Config key (dot notation)")
    config_set.add_argument("value", help="Config value")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize project structure")
    init_parser.add_argument(
        "-d", "--data-dir",
        help="Data directory path",
        default="data",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        if args.command == "run":
            return asyncio.run(cmd_run(args))
        elif args.command == "plugin":
            return asyncio.run(cmd_plugin(args))
        elif args.command == "config":
            return asyncio.run(cmd_config(args))
        elif args.command == "version":
            return cmd_version(args)
        elif args.command == "init":
            return cmd_init(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


async def cmd_run(args) -> int:
    """Run the bot."""
    from AetherPackBot.core.kernel.app_kernel import ApplicationKernel
    
    kernel = ApplicationKernel(
        config_path=args.config,
        data_dir=args.data_dir,
        debug=args.debug,
    )
    
    try:
        await kernel.boot()
        await kernel.run()
    except Exception as e:
        logger.error(f"Runtime error: {e}")
        return 1
    finally:
        await kernel.shutdown()
    
    return 0


async def cmd_plugin(args) -> int:
    """Plugin management commands."""
    if not args.plugin_command:
        print("Usage: aetherpackbot plugin <list|install|uninstall>")
        return 0
    
    if args.plugin_command == "list":
        return await plugin_list_cmd()
    elif args.plugin_command == "install":
        return await plugin_install_cmd(args.source)
    elif args.plugin_command == "uninstall":
        return await plugin_uninstall_cmd(args.name)
    
    return 0


async def plugin_list_cmd() -> int:
    """List installed plugins."""
    from AetherPackBot.core.plugin.manager import PluginManager
    from AetherPackBot.core.kernel.container import ServiceContainer
    
    container = ServiceContainer()
    manager = PluginManager(container)
    
    await manager.discover_plugins()
    
    plugins = manager.get_all_plugins()
    
    if not plugins:
        print("No plugins installed")
        return 0
    
    print("\nInstalled Plugins:")
    print("-" * 60)
    
    for plugin in plugins:
        status = "✓" if plugin.status.name == "RUNNING" else "○"
        builtin = "[builtin]" if plugin.is_builtin else ""
        print(f"  {status} {plugin.name} v{plugin.metadata.version} {builtin}")
        if plugin.metadata.description:
            print(f"      {plugin.metadata.description}")
    
    print(f"\nTotal: {len(plugins)} plugins")
    return 0


async def plugin_install_cmd(source: str) -> int:
    """Install a plugin from source."""
    from pathlib import Path
    import shutil
    
    source_path = Path(source)
    
    if source_path.exists():
        # Local path installation
        if not source_path.is_dir():
            print(f"Error: {source} is not a directory")
            return 1
        
        plugins_dir = Path("data/plugins")
        plugins_dir.mkdir(parents=True, exist_ok=True)
        
        target = plugins_dir / source_path.name
        if target.exists():
            print(f"Error: Plugin {source_path.name} already exists")
            return 1
        
        shutil.copytree(source_path, target)
        print(f"Installed plugin: {source_path.name}")
        return 0
    
    # URL installation
    if source.startswith("http://") or source.startswith("https://"):
        print("URL-based installation not yet implemented")
        return 1
    
    # Git-based installation (github:user/repo)
    if source.startswith("github:"):
        repo = source.replace("github:", "")
        print(f"Installing from GitHub: {repo}")
        
        # Clone repository
        import subprocess
        url = f"https://github.com/{repo}.git"
        
        plugins_dir = Path("data/plugins")
        plugins_dir.mkdir(parents=True, exist_ok=True)
        
        target = plugins_dir / repo.split("/")[-1]
        
        result = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"Error cloning repository: {result.stderr}")
            return 1
        
        print(f"Installed plugin: {repo.split('/')[-1]}")
        return 0
    
    print(f"Error: Unknown source format: {source}")
    return 1


async def plugin_uninstall_cmd(name: str) -> int:
    """Uninstall a plugin."""
    import shutil
    
    plugins_dir = Path("data/plugins")
    target = plugins_dir / name
    
    if not target.exists():
        print(f"Error: Plugin {name} not found")
        return 1
    
    shutil.rmtree(target)
    print(f"Uninstalled plugin: {name}")
    return 0


async def cmd_config(args) -> int:
    """Configuration management commands."""
    if not args.config_command:
        print("Usage: aetherpackbot config <show|set>")
        return 0
    
    if args.config_command == "show":
        return await config_show_cmd()
    elif args.config_command == "set":
        return await config_set_cmd(args.key, args.value)
    
    return 0


async def config_show_cmd() -> int:
    """Show current configuration."""
    from AetherPackBot.core.storage.config import ConfigurationManager
    import json
    
    manager = ConfigurationManager()
    await manager.load()
    
    config_dict = manager.to_dict()
    
    # Mask sensitive values
    def mask_sensitive(d: dict, keys: list[str]) -> dict:
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = mask_sensitive(v, keys)
            elif k in keys and v:
                result[k] = "***"
            else:
                result[k] = v
        return result
    
    masked = mask_sensitive(config_dict, ["api_key", "token", "password", "secret"])
    print(json.dumps(masked, indent=2))
    
    return 0


async def config_set_cmd(key: str, value: str) -> int:
    """Set a configuration value."""
    from AetherPackBot.core.storage.config import ConfigurationManager
    
    manager = ConfigurationManager()
    await manager.load()
    
    # Parse value type
    parsed_value: any = value
    
    if value.lower() == "true":
        parsed_value = True
    elif value.lower() == "false":
        parsed_value = False
    elif value.isdigit():
        parsed_value = int(value)
    elif value.replace(".", "").isdigit():
        parsed_value = float(value)
    
    manager.set(key, parsed_value)
    await manager.save()
    
    print(f"Set {key} = {parsed_value}")
    return 0


def cmd_version(args) -> int:
    """Show version information."""
    print("AetherPackBot v1.0.0")
    print(f"Python {sys.version}")
    return 0


def cmd_init(args) -> int:
    """Initialize project structure."""
    data_dir = Path(args.data_dir)
    
    # Create directories
    dirs = [
        data_dir / "config",
        data_dir / "plugins",
        data_dir / "temp",
        data_dir / "logs",
        data_dir / "cache",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"Created: {d}")
    
    # Create default config
    config_path = data_dir / "config" / "config.json"
    if not config_path.exists():
        import json
        
        default_config = {
            "web": {
                "host": "0.0.0.0",
                "port": 6185,
                "admin_username": "aetherpackbot",
                "admin_password": "aetherpackbot",
            },
            "logging": {
                "level": "INFO",
            },
            "providers": [],
            "platforms": [],
            "agent": {
                "enabled": True,
            },
        }
        
        config_path.write_text(json.dumps(default_config, indent=2))
        print(f"Created: {config_path}")
    
    print("\nInitialization complete!")
    print(f"Run 'python main.py' or 'aetherpackbot run' to start the bot.")
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
