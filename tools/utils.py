# utils.py
import logging
from datetime import datetime
import threading

def log_activity(message: str, thread_id: str = "MAIN") -> None:
    """Enhanced activity logging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    logging.info(f"[{timestamp}] [{threading.current_thread().name}] [{thread_id}] {message}")