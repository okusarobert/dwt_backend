import logging
import datetime
import json
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        return json.dumps(log_record)


def setup_logging():
    logger = logging.getLogger("betting_service")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.handlers = []  # Remove any existing handlers
    logger.addHandler(console_handler)
    return logger


