"""
Engine Manager
Manages multiple chess engines and their configurations
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """Engine configuration"""
    name: str
    path: str
    enabled: bool = True
    time_control: int = 60000  # Default 60 seconds
    options: Dict = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}


class EngineManager:
    """
    Manages engine registry and configurations

    Features:
    - Auto-discovery of engines
    - Configuration persistence
    - Engine validation
    """

    def __init__(self, config_file: str = "config/engines.json"):
        """
        Initialize Engine Manager

        Args:
            config_file: Path to engine configuration file
        """
        self.config_file = Path(config_file)
        self.engines: Dict[str, EngineConfig] = {}

        # Create config directory if needed
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load or create config
        self.load_config()

    def load_config(self):
        """Load engine configurations from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)

                self.engines = {
                    name: EngineConfig(**config)
                    for name, config in data.items()
                }

                logger.info(f"Loaded {len(self.engines)} engine configurations")

            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self.engines = {}
        else:
            logger.info("No engine config found, creating new")
            self.discover_engines()

    def save_config(self):
        """Save engine configurations to file"""
        try:
            data = {
                name: asdict(config)
                for name, config in self.engines.items()
            }

            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.engines)} engine configurations")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def discover_engines(self):
        """Auto-discover engines in Engines directory"""
        engines_dir = Path("Engines")

        if not engines_dir.exists():
            logger.warning(f"Engines directory not found: {engines_dir}")
            return

        # Find all .exe files
        exe_files = list(engines_dir.glob("*.exe"))

        logger.info(f"Found {len(exe_files)} engine executables")

        for exe_path in exe_files:
            engine_name = exe_path.stem
            self.add_engine(
                name=engine_name,
                path=str(exe_path),
                save=False  # Save once at the end
            )

        self.save_config()

    def add_engine(self,
                   name: str,
                   path: str,
                   enabled: bool = True,
                   time_control: int = 60000,
                   options: Optional[Dict] = None,
                   save: bool = True) -> bool:
        """
        Add or update engine configuration

        Args:
            name: Engine identifier
            path: Path to engine executable
            enabled: Whether engine is enabled
            time_control: Default time control (ms)
            options: UCI options dict
            save: Save config after adding

        Returns:
            True if successful
        """
        try:
            # Validate path
            if not Path(path).exists():
                logger.error(f"Engine path does not exist: {path}")
                return False

            config = EngineConfig(
                name=name,
                path=path,
                enabled=enabled,
                time_control=time_control,
                options=options or {}
            )

            self.engines[name] = config

            if save:
                self.save_config()

            logger.info(f"Added engine: {name} at {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to add engine: {e}")
            return False

    def remove_engine(self, name: str) -> bool:
        """Remove engine from registry"""
        if name in self.engines:
            del self.engines[name]
            self.save_config()
            logger.info(f"Removed engine: {name}")
            return True
        return False

    def get_engine(self, name: str) -> Optional[EngineConfig]:
        """Get engine configuration by name"""
        return self.engines.get(name)

    def list_engines(self, enabled_only: bool = False) -> List[EngineConfig]:
        """
        Get list of engine configurations

        Args:
            enabled_only: Only return enabled engines

        Returns:
            List of engine configurations
        """
        engines = list(self.engines.values())

        if enabled_only:
            engines = [e for e in engines if e.enabled]

        return engines

    def enable_engine(self, name: str, enabled: bool = True):
        """Enable or disable engine"""
        if name in self.engines:
            self.engines[name].enabled = enabled
            self.save_config()
            logger.info(f"Engine {name} {'enabled' if enabled else 'disabled'}")

    def update_engine_options(self, name: str, options: Dict):
        """Update UCI options for engine"""
        if name in self.engines:
            self.engines[name].options.update(options)
            self.save_config()
            logger.info(f"Updated options for {name}")

    def validate_engine(self, name: str) -> bool:
        """
        Validate that engine works

        Args:
            name: Engine name

        Returns:
            True if engine is valid
        """
        from .uci_interface import UCIEngine

        config = self.get_engine(name)
        if not config:
            logger.error(f"Engine not found: {name}")
            return False

        try:
            with UCIEngine(config.path) as engine:
                if engine.initialize():
                    logger.info(f"Engine validated: {engine.name}")
                    return True
                else:
                    logger.error(f"Engine failed to initialize: {name}")
                    return False

        except Exception as e:
            logger.error(f"Engine validation failed for {name}: {e}")
            return False

    def get_engine_info(self, name: str) -> Optional[Dict]:
        """
        Get detailed engine information

        Args:
            name: Engine name

        Returns:
            Dict with engine info or None
        """
        from .uci_interface import UCIEngine

        config = self.get_engine(name)
        if not config:
            return None

        try:
            with UCIEngine(config.path) as engine:
                if engine.initialize():
                    return {
                        "name": engine.name,
                        "author": engine.author,
                        "path": config.path,
                        "options": engine.options,
                        "supports_mate_search": engine.supports_mate_search
                    }

        except Exception as e:
            logger.error(f"Failed to get engine info: {e}")

        return None
