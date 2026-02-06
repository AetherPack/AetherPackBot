"""
Application Kernel - Central orchestrator of the application.

The kernel is responsible for:
- Bootstrapping all services and components
- Managing the service container
- Coordinating lifecycle events
- Providing access to core services
"""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from typing import Any

from aetherpackbot.kernel.container import ServiceContainer
from aetherpackbot.kernel.lifecycle import LifecycleManager, LifecycleState
from aetherpackbot.kernel.logging import LogManager, get_logger


class ApplicationKernel:
    """
    Central application kernel that orchestrates all components.
    
    The kernel follows a two-phase initialization pattern:
    1. Construction (__init__): Set up basic configuration
    2. Boot (boot): Initialize and start all services
    
    Example:
        kernel = ApplicationKernel()
        await kernel.boot()
        await kernel.run_forever()
    """
    
    def __init__(
        self,
        webui_dir: str | None = None,
        config_path: str | None = None,
        debug: bool = False,
    ) -> None:
        """
        Create a new application kernel.
        
        Args:
            webui_dir: Optional path to custom WebUI static files
            config_path: Optional path to configuration file
            debug: Enable debug mode
        """
        self._webui_dir = webui_dir
        self._config_path = config_path
        self._debug = debug
        
        # Core systems
        self._container = ServiceContainer()
        self._lifecycle = LifecycleManager()
        self._logger = get_logger("kernel")
        
        # Application state
        self._shutdown_event = asyncio.Event()
        self._is_booted = False
        
        # Register core services in container
        self._register_core_services()
    
    def _register_core_services(self) -> None:
        """Register core services in the dependency container."""
        self._container.register_instance(ServiceContainer, self._container)
        self._container.register_instance(LifecycleManager, self._lifecycle)
        self._container.register_singleton(LogManager)
    
    async def boot(self) -> None:
        """
        Boot the application kernel.
        
        This initializes all services and starts the application.
        """
        if self._is_booted:
            return
        
        self._logger.info("Booting application kernel...")
        
        try:
            # Phase 1: Initialize data directories
            await self._initialize_directories()
            
            # Phase 2: Load configuration
            await self._load_configuration()
            
            # Phase 3: Register services
            await self._register_services()
            
            # Phase 4: Start all services
            await self._lifecycle.start_all()
            
            # Phase 5: Set up signal handlers
            self._setup_signal_handlers()
            
            self._is_booted = True
            self._logger.info("Application kernel booted successfully")
            
        except Exception as e:
            self._logger.exception(f"Failed to boot kernel: {e}")
            raise
    
    async def _initialize_directories(self) -> None:
        """Create required data directories."""
        directories = [
            "data",
            "data/config",
            "data/plugins",
            "data/temp",
            "data/logs",
            "data/storage",
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self._logger.debug("Data directories initialized")
    
    async def _load_configuration(self) -> None:
        """Load application configuration."""
        from aetherpackbot.storage.config import ConfigurationManager
        
        config_manager = ConfigurationManager(self._config_path)
        await config_manager.load()
        
        self._container.register_instance(ConfigurationManager, config_manager)
        self._logger.debug("Configuration loaded")
    
    async def _register_services(self) -> None:
        """Register and initialize all application services."""
        # Import and register all service modules
        
        # Storage layer
        from aetherpackbot.storage.database import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        self._container.register_instance(DatabaseManager, db_manager)
        self._lifecycle.register(db_manager, priority=100)
        
        # Event system
        from aetherpackbot.messaging.events import EventDispatcher
        event_dispatcher = EventDispatcher()
        self._container.register_instance(EventDispatcher, event_dispatcher)
        self._lifecycle.register(event_dispatcher, priority=90)
        
        # Provider manager
        from aetherpackbot.providers.manager import ProviderManager
        provider_manager = ProviderManager(self._container)
        await provider_manager.initialize()
        self._container.register_instance(ProviderManager, provider_manager)
        self._lifecycle.register(provider_manager, priority=80)
        
        # Platform manager
        from aetherpackbot.platforms.manager import PlatformManager
        platform_manager = PlatformManager(self._container, event_dispatcher)
        self._container.register_instance(PlatformManager, platform_manager)
        self._lifecycle.register(platform_manager, priority=70)
        
        # Plugin system
        from aetherpackbot.plugins.manager import PluginManager
        plugin_manager = PluginManager(self._container)
        await plugin_manager.scan_and_load()
        self._container.register_instance(PluginManager, plugin_manager)
        self._lifecycle.register(plugin_manager, priority=60)
        
        # Agent system
        from aetherpackbot.agents.orchestrator import AgentOrchestrator
        agent_orchestrator = AgentOrchestrator(self._container)
        self._container.register_instance(AgentOrchestrator, agent_orchestrator)
        self._lifecycle.register(agent_orchestrator, priority=50)
        
        # Message processor (pipeline)
        from aetherpackbot.messaging.processor import MessageProcessor
        message_processor = MessageProcessor(self._container)
        self._container.register_instance(MessageProcessor, message_processor)
        self._lifecycle.register(message_processor, priority=40)
        
        # Web API server
        from aetherpackbot.webapi.server import WebServer
        web_server = WebServer(self._container, self._webui_dir)
        self._container.register_instance(WebServer, web_server)
        self._lifecycle.register(web_server, priority=30)
        
        self._logger.debug("All services registered")
    
    def _setup_signal_handlers(self) -> None:
        """Set up OS signal handlers for graceful shutdown."""
        if os.name != "nt":  # Not Windows
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
    
    async def run_forever(self) -> None:
        """
        Run the application until shutdown.
        
        This method blocks until shutdown() is called or a signal is received.
        """
        if not self._is_booted:
            await self.boot()
        
        self._logger.info("Application running. Press Ctrl+C to stop.")
        await self._shutdown_event.wait()
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the application.
        
        Stops all services in reverse dependency order.
        """
        if self._shutdown_event.is_set():
            return
        
        self._logger.info("Initiating shutdown sequence...")
        
        try:
            await self._lifecycle.stop_all()
            await self._container.dispose()
            self._logger.info("All services stopped successfully")
        except Exception as e:
            self._logger.exception(f"Error during shutdown: {e}")
        finally:
            self._shutdown_event.set()
    
    @property
    def container(self) -> ServiceContainer:
        """Get the service container."""
        return self._container
    
    @property
    def lifecycle(self) -> LifecycleManager:
        """Get the lifecycle manager."""
        return self._lifecycle
    
    @property
    def is_running(self) -> bool:
        """Check if the application is running."""
        return self._lifecycle.state == LifecycleState.RUNNING
    
    async def resolve(self, service_type: type) -> Any:
        """Resolve a service from the container."""
        return await self._container.resolve(service_type)
