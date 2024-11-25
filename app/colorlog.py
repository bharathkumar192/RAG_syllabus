# app/logger_config.py
import logging
import colorlog

def configure_logger():
    """Configure global logger with colors."""
    # Define log colors
    log_colors = {
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # Define formatter with colors
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_colors=log_colors
    )

    # Set up root logger
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set global log level
    logger.addHandler(handler)
