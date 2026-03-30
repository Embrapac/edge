import logging
import structlog

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(name: str):
    return logging.getLogger(name)

def get_struct_logger(name: str):
    return structlog.get_logger(name)