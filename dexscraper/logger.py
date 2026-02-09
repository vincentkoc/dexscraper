"""Centralized logging configuration for dexscraper."""

import logging
import sys
from datetime import datetime
from types import TracebackType
from typing import Any, Callable, Optional


class DexScraperLogger:
    """Centralized logger for the dexscraper package."""

    _instance: Optional["DexScraperLogger"] = None
    _initialized: bool = False

    def __new__(cls) -> "DexScraperLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("dexscraper")
        if not self._initialized:
            self._setup_default_logger()
            self._initialized = True

    def _setup_default_logger(self) -> None:
        """Setup default logging configuration."""
        self.logger = logging.getLogger("dexscraper")

        # Default to ERROR level to keep output clean
        self.logger.setLevel(logging.ERROR)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.ERROR)

        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(console_handler)

    def set_debug(self, debug: bool = True) -> None:
        """Enable or disable debug logging."""
        if debug:
            self.logger.setLevel(logging.DEBUG)
            # Update handler levels
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.ERROR)
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.ERROR)

    def set_level(self, level: int) -> None:
        """Set logging level."""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

    def add_file_handler(self, filename: str, level: int = logging.INFO) -> None:
        """Add file logging handler."""
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger


def get_logger() -> logging.Logger:
    """Get the dexscraper logger instance.

    Returns:
        logging.Logger: Configured logger for dexscraper
    """
    return DexScraperLogger().get_logger()


def set_debug_logging(debug: bool = True) -> None:
    """Enable or disable debug logging globally.

    Args:
        debug: Whether to enable debug logging
    """
    DexScraperLogger().set_debug(debug)


def add_file_logging(filename: str, level: int = logging.INFO) -> None:
    """Add file logging to the global logger.

    Args:
        filename: Path to log file
        level: Logging level for file handler
    """
    DexScraperLogger().add_file_handler(filename, level)


class LogContext:
    """Context manager for temporary logging level changes."""

    def __init__(self, level: int) -> None:
        self.level = level
        self.original_level: Optional[int] = None
        self.logger_instance = DexScraperLogger()

    def __enter__(self) -> "LogContext":
        self.original_level = self.logger_instance.logger.level
        self.logger_instance.set_level(self.level)
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.original_level is not None:
            self.logger_instance.set_level(self.original_level)


class PerformanceLogger:
    """Performance logging utilities."""

    def __init__(self, operation_name: str) -> None:
        self.operation_name = operation_name
        self.logger = get_logger()
        self.start_time: Optional[datetime] = None

    def __enter__(self) -> "PerformanceLogger":
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation_name}")
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.start_time:
            duration = datetime.now() - self.start_time
            duration_ms = duration.total_seconds() * 1000

            if exc_type is None:
                self.logger.debug(
                    f"Completed {self.operation_name} in {duration_ms:.2f}ms"
                )
            else:
                self.logger.error(
                    f"Failed {self.operation_name} after {duration_ms:.2f}ms: {exc_val}"
                )


def log_performance(
    operation_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for logging function performance.

    Args:
        operation_name: Name of the operation being logged
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with PerformanceLogger(operation_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Common log patterns
def log_extraction_start(token_count: int = 0) -> None:
    """Log the start of token extraction."""
    logger = get_logger()
    logger.info(f"Starting token extraction (target: {token_count} tokens)")


def log_extraction_success(
    batch_size: int, high_confidence: int, duration_ms: float
) -> None:
    """Log successful token extraction."""
    logger = get_logger()
    logger.info(
        f"Extraction successful: {batch_size} tokens, {high_confidence} high-confidence ({duration_ms:.2f}ms)"
    )


def log_extraction_failure(error: Exception, duration_ms: float) -> None:
    """Log failed token extraction."""
    logger = get_logger()
    logger.error(f"Extraction failed after {duration_ms:.2f}ms: {error}")


def log_websocket_connection(url: str) -> None:
    """Log WebSocket connection attempt."""
    logger = get_logger()
    logger.debug(f"Connecting to WebSocket: {url}")


def log_websocket_success() -> None:
    """Log successful WebSocket connection."""
    logger = get_logger()
    logger.info("WebSocket connection established")


def log_websocket_failure(error: Exception, retry_count: int) -> None:
    """Log WebSocket connection failure."""
    logger = get_logger()
    logger.warning(f"WebSocket connection failed (attempt {retry_count}): {error}")


def log_binary_analysis(data_size: int) -> None:
    """Log binary data analysis start."""
    logger = get_logger()
    logger.debug(f"Analyzing {data_size} bytes of binary data")


def log_token_profile_built(symbol: str, confidence: float, field_count: int) -> None:
    """Log successful token profile construction."""
    logger = get_logger()
    logger.debug(
        f"Built profile: {symbol} (confidence: {confidence:.0%}, fields: {field_count})"
    )
