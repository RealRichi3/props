import logging

from src.utils.logger import new_logger, LoggerOptions
from src.utils.config import Config


class TestLogger:
    def setup_method(self):
        """Set up test fixtures before each test method."""
        logging.getLogger().handlers.clear()

    def test_logger_creation_with_default_config(self):
        """Test creating a logger with default configuration."""
        options: LoggerOptions = {"name": "test_logger"}
        logger = new_logger(options)

        assert logger.name == "test_logger"
        assert isinstance(logger, logging.Logger)

    def test_logger_creation_with_custom_level(self):
        """Test creating a logger with custom log level."""
        options: LoggerOptions = {"name": "test_logger_custom", "level": logging.DEBUG}
        logger = new_logger(options)

        assert logger.name == "test_logger_custom"
        assert logger.level == logging.DEBUG

    def test_logger_creation_with_config_manager(self):
        """Test creating a logger with custom config manager."""
        config = Config()
        config.set("logging", "log_level", logging.WARNING)

        options: LoggerOptions = {"name": "test_logger_config"}
        logger = new_logger(options, config)

        assert logger.name == "test_logger_config"

    def test_logger_formatting(self):
        """Test that logger has proper formatter."""
        options: LoggerOptions = {"name": "test_format_logger"}
        logger = new_logger(options)

        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter is not None

    def test_logger_no_duplicate_handlers(self):
        """Test that calling new_logger multiple times doesn't create duplicate handlers."""
        options: LoggerOptions = {"name": "test_no_duplicate"}

        logger1 = new_logger(options)
        initial_handler_count = len(logger1.handlers)

        logger2 = new_logger(options)
        final_handler_count = len(logger2.handlers)

        assert initial_handler_count == final_handler_count
        assert logger1 is logger2

    def test_logger_with_different_names(self):
        """Test creating loggers with different names."""
        options1: LoggerOptions = {"name": "logger_one"}
        options2: LoggerOptions = {"name": "logger_two"}

        logger1 = new_logger(options1)
        logger2 = new_logger(options2)

        assert logger1.name != logger2.name
        assert logger1 is not logger2

    def test_logger_optional_level_handling(self):
        """Test that optional level parameter works correctly."""
        # Test with None level
        options_none: LoggerOptions = {"name": "test_none_level", "level": None}
        logger_none = new_logger(options_none)
        assert isinstance(logger_none, logging.Logger)

        # Test without level key
        options_no_level: LoggerOptions = {"name": "test_no_level"}
        logger_no_level = new_logger(options_no_level)
        assert isinstance(logger_no_level, logging.Logger)
