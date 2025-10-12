"""
HITL Node - Separate file for Human-in-the-Loop validation
Handles user input with timeout
"""

import logging
import queue
from threading import Thread
from typing import Dict, Any

logger = logging.getLogger(__name__)


def hitl_pause(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pause workflow for human input."""
    thread_id = state.get("thread_id", "unknown")
    timeout = state.get("hitl_timeout_seconds", 30)  # Default 30s

    logger.info(f"[HITL-{thread_id}] Waiting for human decision...")

    q = queue.Queue()

    def get_input(q):
        try:
            resp = input("Approve? (Y/N) [default Y]: ").strip().upper() or "Y"
            q.put("approve" if resp == "Y" else "reject")
        except EOFError:
            q.put("approve")

    thread = Thread(target=get_input, args=(q,))
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        decision = "approve"
        logger.info(f"[HITL-{thread_id}] Timeout - auto-approving")
    else:
        decision = q.get()

    state["human_decision"] = decision
    return state