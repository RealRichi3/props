import copy
import json
import os
from typing import Any, Dict, Optional, Literal
from datetime import datetime
from dataclasses import dataclass, asdict


def _resolve_path_from_project_root(path: str) -> str:
    """
    Resolve path to absolute path from project root.

    Args:
        path: Path that could be relative or absolute

    Returns:
        Absolute path
    """
    if os.path.isabs(path):
        return path
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        full_path = os.path.join(project_root, path)
        return os.path.abspath(full_path)


@dataclass
class ConfigGlobals:
    timestamp: Optional[str] = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir: Optional[str] = _resolve_path_from_project_root("./out_dir")


ConfigSection = Literal["simulation", "logging", "prediction", "traffic", "global"]


@dataclass
class ConfigOption:
    section: Optional[ConfigSection] = None
    global_config_overides: Optional[ConfigGlobals] = None
    config_path: Optional[str] = None


class Config:
    """
    Centralized configuration management.

    This class provides methods for loading configuration from multiple sources,
    validating configuration values, and accessing configuration in a consistent way.
    """

    def __init__(self, opts: Optional[ConfigOption] = None):
        """
        Initialize the configuration manager.

        Args:
            opts: Configuration options including global overrides
        """
        # Pass global overrides to default config loading
        global_overrides = opts.global_config_overides if opts else None
        self.config = self._load_default_config(global_overrides)

        if opts and opts.config_path:
            self._load_config_from_file(opts.config_path)

    def _load_default_config(
        self, globals: Optional[ConfigGlobals] = ConfigGlobals()
    ) -> Dict[str, Any]:
        """
        Load default configuration values.

        Returns:
            Dictionary containing default configuration
        """
        # Merge defaults with global overrides
        global_config = {
            **asdict(ConfigGlobals()),
            **(asdict(globals) if globals else {}),
        }

        if "out_dir" in global_config:
            global_config["out_dir"] = _resolve_path_from_project_root(
                global_config["out_dir"]
            )

        return {
            "global": global_config,
            "prediction": {
                "max_route_length": 10,
                "max_vehicle_history": 1000,
                "prediction_timeout_ms": 100,
                "accuracy_window_size": 50,
                "persistence_interval": 1,
                "cleanup_threshold": 10000,
                "min_confidence_threshold": 0.1,
                "persistence_file": "out_data/prediction_data.json",
                "use_json_persistence": True,
            },
            "simulation": {
                "sumo_binary": "sumo_binary",
                "config_file": "sumo/cross.sumocfg",
                "port": 1337,
                "num_clients": 1,
                "gui": True,
                "step_length": 0.1,
                "delay": 200,
                "auto_start": True,
                "auto_reconnect": True,
                "max_reconnect_attempts": 3,
                "reconnect_delay": 1.0,
            },
            "traffic": {},
            "logging": {
                "log_level": "INFO",
                "log_format": "json",
            },
            "junction": {},
        }

    def _load_config_from_file(self, config_path: str) -> bool:
        """
        Load configuration from a file.

        Args:
            config_path: Path to the configuration file

        Returns:
            True if the configuration was loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(config_path):
                print(f"Configuration file not found: {config_path}")
                return False

            with open(config_path) as f:
                file_config = json.load(f)
                self._merge_config(file_config)
            return True
        except json.JSONDecodeError as e:
            print(f"Error parsing configuration file {config_path}: {e}")
            return False
        except Exception as e:
            print(f"Error loading configuration from {config_path}: {e}")
            return False

    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge new configuration with existing configuration.

        Args:
            new_config: New configuration to merge
        """
        for section, values in new_config.items():
            if section in self.config:
                if isinstance(values, dict) and isinstance(self.config[section], dict):
                    self.config[section].update(values)
                else:
                    self.config[section] = values
            else:
                self.config[section] = values

        # Resolve out_dir path if it was updated in global section
        if "global" in new_config and "out_dir" in new_config["global"]:
            self.config["global"]["out_dir"] = _resolve_path_from_project_root(
                self.config["global"]["out_dir"]
            )

    def get(self, section: ConfigSection, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if the key is not found

        Returns:
            Configuration value or default
        """
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default

    def get_section(self, section: ConfigSection) -> Dict[str, Any]:
        """
        Get an entire configuration section.

        Args:
            section: Configuration section

        Returns:
            Dictionary containing the section or empty dictionary if not found
        """
        return self.config.get(section, {}).copy()

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            value: Configuration value
        """
        if section not in self.config:
            self.config[section] = {}

        # Resolve out_dir path if being set in global section
        if section == "global" and key == "out_dir" and isinstance(value, str):
            value = _resolve_path_from_project_root(value)

        self.config[section][key] = value

    def load_from_env(self, prefix: str = "APP_") -> None:
        """
        Load configuration from environment variables.

        Environment variables should be in the format:
        {prefix}{SECTION}_{KEY}={VALUE}

        For example:
        APP_PREDICTION_MAX_ROUTE_LENGTH=10

        Args:
            prefix: Prefix for environment variables (default: 'APP_')
        """
        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                env_var = env_var[len(prefix) :]

                parts = env_var.split("_", 1)
                if len(parts) != 2:
                    continue

                section = parts[0].lower()
                key = parts[1].lower()

                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)

                self.set(section, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.

        Returns:
            Dictionary containing all configuration (deep copy)
        """
        return copy.deepcopy(self.config)

    def save_to_file(self, config_path: str) -> bool:
        """
        Save configuration to a file.

        Args:
            config_path: Path to the configuration file

        Returns:
            True if the configuration was saved successfully, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving configuration to {config_path}: {e}")
            return False
