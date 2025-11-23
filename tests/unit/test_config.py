import pytest
import json
import os
import tempfile

from src.utils.config import Config


class TestConfig:
    """Test suite for the configuration management system."""

    def test_default_config_loading(self):
        """Test that default configuration is loaded correctly."""
        config = Config()

        # Check that default sections exist
        assert "prediction" in config.to_dict()
        assert "simulation" in config.to_dict()
        assert "traffic" in config.to_dict()
        assert "logging" in config.to_dict()
        assert "junction" in config.to_dict()

        # Check some default values
        prediction_config = config.get_section("prediction")
        assert prediction_config["max_route_length"] == 10
        assert prediction_config["max_vehicle_history"] == 1000
        assert prediction_config["prediction_timeout_ms"] == 100

        logging_config = config.get_section("logging")
        assert logging_config["log_level"] == "INFO"
        assert logging_config["log_format"] == "json"

    def test_get_configuration_value(self):
        """Test getting individual configuration values."""
        config = Config()

        # Test existing values
        assert config.get("prediction", "max_route_length") == 10
        assert config.get("logging", "log_level") == "INFO"

        # Test default values
        assert config.get("prediction", "nonexistent_key", "default") == "default"
        assert config.get("nonexistent_section", "key", "default") == "default"

    def test_set_configuration_value(self):
        """Test setting configuration values."""
        config = Config()

        # Set new value in existing section
        config.set("prediction", "new_key", "new_value")
        assert config.get("prediction", "new_key") == "new_value"

        # Set value in new section
        config.set("new_section", "new_key", "new_value")
        assert config.get("new_section", "new_key") == "new_value"

    def test_get_section(self):
        """Test getting entire configuration sections."""
        config = Config()

        prediction_section = config.get_section("prediction")
        assert isinstance(prediction_section, dict)
        assert "max_route_length" in prediction_section

        # Test nonexistent section
        nonexistent_section = config.get_section("nonexistent")
        assert nonexistent_section == {}

        # Test that returned section is a copy (modifications don't affect original)
        prediction_section["test_modification"] = "test"
        original_section = config.get_section("prediction")
        assert "test_modification" not in original_section

    def test_config_file_loading(self):
        """Test loading configuration from a file."""
        test_config = {
            "prediction": {
                "max_route_length": 20,
                "custom_setting": "custom_value"
            },
            "custom_section": {
                "custom_key": "custom_value"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # Check that file values override defaults
            assert config.get("prediction", "max_route_length") == 20
            assert config.get("prediction", "custom_setting") == "custom_value"

            # Check that default values are still present
            assert config.get("prediction", "max_vehicle_history") == 1000

            # Check custom section
            assert config.get("custom_section", "custom_key") == "custom_value"

        finally:
            os.unlink(config_path)

    def test_invalid_config_file(self):
        """Test handling of invalid configuration files."""
        # Test nonexistent file
        config = Config("nonexistent_file.json")
        # Should still have defaults
        assert config.get("prediction", "max_route_length") == 10

        # Test invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            invalid_config_path = f.name

        try:
            config = Config(invalid_config_path)
            # Should still have defaults
            assert config.get("prediction", "max_route_length") == 10

        finally:
            os.unlink(invalid_config_path)

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        config = Config()

        # Set some environment variables
        os.environ["APP_PREDICTION_MAX_ROUTE_LENGTH"] = "50"
        os.environ["APP_LOGGING_LOG_LEVEL"] = "DEBUG"
        os.environ["APP_CUSTOM_BOOLEAN"] = "true"
        os.environ["APP_CUSTOM_NUMBER"] = "123"
        os.environ["APP_CUSTOM_FLOAT"] = "123.45"

        try:
            config.load_from_env("APP_")

            assert config.get("prediction", "max_route_length") == 50
            assert config.get("logging", "log_level") == "DEBUG"
            assert config.get("custom", "boolean") is True
            assert config.get("custom", "number") == 123
            assert config.get("custom", "float") == 123.45

        finally:
            # Clean up environment variables
            for key in ["APP_PREDICTION_MAX_ROUTE_LENGTH", "APP_LOGGING_LOG_LEVEL",
                       "APP_CUSTOM_BOOLEAN", "APP_CUSTOM_NUMBER", "APP_CUSTOM_FLOAT"]:
                if key in os.environ:
                    del os.environ[key]

    def test_save_and_load_config(self):
        """Test saving configuration to file and loading it back."""
        config = Config()
        config.set("test_section", "test_key", "test_value")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name

        try:
            # Save configuration
            success = config.save_to_file(config_path)
            assert success is True

            # Load configuration in new instance
            new_config = Config(config_path)
            assert new_config.get("test_section", "test_key") == "test_value"
            assert new_config.get("prediction", "max_route_length") == 10  # Defaults should be preserved

        finally:
            os.unlink(config_path)

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Config()
        config.set("test", "key", "value")

        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["test"]["key"] == "value"

        # Test that it's a deep copy
        config_dict["test"]["key"] = "modified"
        assert config.get("test", "key") == "value"  # Original should be unchanged

    def test_config_merge(self):
        """Test merging configurations."""
        config = Config()

        # Test merging with existing section
        original_max_route = config.get("prediction", "max_route_length")
        new_config_data = {
            "prediction": {
                "max_route_length": 99,
                "new_prediction_key": "new_value"
            }
        }

        config._merge_config(new_config_data)

        assert config.get("prediction", "max_route_length") == 99
        assert config.get("prediction", "new_prediction_key") == "new_value"
        # Other prediction values should still exist
        assert config.get("prediction", "max_vehicle_history") == 1000