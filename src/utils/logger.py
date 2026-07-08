import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from src.config import get_settings


class JSONFormatter(logging.Formatter):
    """Format logs as structured JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "candidate_id"):
            log_data["candidate_id"] = str(record.candidate_id)
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "details"):
            log_data["details"] = record.details
        if hasattr(record, "apify_run_id"):
            log_data["apify_run_id"] = record.apify_run_id
        if hasattr(record, "retry_count"):
            log_data["retry_count"] = record.retry_count
            
        return json.dumps(log_data)


def setup_logger(name: str = "saral_pipeline") -> logging.Logger:
    """Set up logger with JSON file handler."""
    settings = get_settings()
    
    # Create logs directory
    logs_dir = Path(settings.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler with JSON format
    log_file = logs_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler with simple format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_success(logger: logging.Logger, candidate_id: UUID, details: Optional[dict] = None):
    """Log a successful candidate update."""
    logger.info(
        f"Successfully processed candidate {candidate_id}",
        extra={"candidate_id": candidate_id, "event": "candidate_success", "details": details}
    )


def log_failure(logger: logging.Logger, candidate_id: UUID, reason: str, details: Optional[dict] = None):
    """Log a failed candidate."""
    logger.error(
        f"Failed candidate {candidate_id}: {reason}",
        extra={"candidate_id": candidate_id, "event": "candidate_failed", "details": details, "reason": reason}
    )


def log_circuit_breaker(logger: logging.Logger, failure_count: int, success_count: int):
    """Log circuit breaker trigger."""
    logger.critical(
        f"CIRCUIT BREAKER TRIGGERED: {failure_count} failures, {success_count} successes. Halting pipeline.",
        extra={"event": "circuit_breaker", "failure_count": failure_count, "success_count": success_count}
    )