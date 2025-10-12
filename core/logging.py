import logging
from typing import Dict, Any, List
from threading import Lock

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

stats_lock = Lock()
activity_lock = Lock()

processing_stats = {
    'workflows_executed': 0,
    'code_prs_created': 0,
    'issues_processed': 0,
    'successful_reviews': 0,
    'rebuild_cycles': 0,
    'tokens_used': 0,
    'planner_tokens': 0,
    'developer_tokens': 0,
    'reviewer_tokens': 0,
    'rebuilder_tokens': 0,
    'errors': 0,
    'taskagent_generations': 0,
    'developer_generations': 0,
    'reviewer_generations': 0,
    'rebuilder_generations': 0,
    'tasks_completed': 0,
    'tasks_failed': 0,
    'tasks_pending': 0,
    'tasks_moved_to_hitl': 0,
    'average_sonar_score': 0.0
}

activity_logs: List[Dict[str, Any]] = []

def safe_stats_update(updates: Dict[str, Any]) -> None:
    """Thread-safe statistics update"""
    with stats_lock:
        for key, value in updates.items():
            if key in processing_stats:
                processing_stats[key] += value

def safe_activity_log(entry: Dict[str, Any]) -> None:
    """Thread-safe activity log append"""
    with activity_lock:
        activity_logs.insert(0, entry)  # Insert at beginning for reverse chronological
        if len(activity_logs) > 50:  # Keep last 50 logs
            activity_logs.pop()