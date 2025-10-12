"""
MCP JIRA Client Tool
- Implements get_project_issues_mcp_tool for fetching complete JIRA issues
- Added get_todo_issues_mcp_tool for fetching only "To Do" issues
- Added get_jira_client for creating JIRA instance
- Uses project key from .env/config
- Fetches issues with compatible parsed format
- Thread-safe logging
"""

import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from threading import Lock
from dotenv import load_dotenv
from jira import JIRA, JIRAError

from config.settings import config

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread-safe lock for JIRA operations
jira_lock = Lock()

# Statistics tracking
mcp_stats = {
    'fetches': 0,
    'todo_fetches': 0,
    'successful_fetches': 0,
    'failed_fetches': 0,
    'total_issues_fetched': 0,
    'errors': 0
}

stats_lock = Lock()


def update_mcp_stats(key: str, value: int = 1) -> None:
    """Thread-safe statistics update"""
    with stats_lock:
        if key in mcp_stats:
            mcp_stats[key] += value


def get_jira_client() -> JIRA:
    """Create and return a JIRA client instance"""
    if not all([config.JIRA_SERVER, config.JIRA_EMAIL, config.JIRA_TOKEN]):
        raise ValueError("JIRA configuration incomplete (server, email, or token missing)")

    return JIRA(
        server=config.JIRA_SERVER,
        basic_auth=(config.JIRA_EMAIL, config.JIRA_TOKEN),
        options={'verify': True}  # Set to False if self-signed cert, but not recommended
    )


def get_project_issues_mcp_tool(thread_id: str) -> Dict[str, Any]:
    """
    Fetch ALL issues from the configured JIRA project for design document.

    Args:
        thread_id: Thread identifier for logging

    Returns:
        Dict with 'success', 'issues' (list of parsed issue dicts), or 'error'
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_prefix = f"[{timestamp}] [MCP-JIRA-ALL] [{thread_id}]"

    update_mcp_stats('fetches')

    if not all([config.JIRA_SERVER, config.JIRA_EMAIL, config.JIRA_TOKEN, config.PROJECT_KEY]):
        error_msg = "JIRA configuration incomplete (server, email, token, or project_key missing)"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('failed_fetches')
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg,
            'issues': []
        }

    try:
        with jira_lock:
            logger.info(f"{log_prefix} Connecting to JIRA server: {config.JIRA_SERVER}")
            jira = get_jira_client()

            logger.info(f"{log_prefix} Fetching ALL issues for project: {config.PROJECT_KEY}")
            jql = f'project = "{config.PROJECT_KEY}" ORDER BY created ASC'

            issues = jira.search_issues(
                jql,
                maxResults=1000,  # Adjust based on project size
                fields="key,summary,description,status,priority,issuetype,components,labels,created,updated"
            )

            parsed_issues: List[Dict[str, Any]] = []
            for issue in issues:
                try:
                    issue_data = {
                        'key': issue.key,
                        'summary': getattr(issue.fields, 'summary', '') or '',
                        'description': getattr(issue.fields, 'description', '') or '',
                        'status': getattr(issue.fields.status, 'name', 'Unknown') if hasattr(issue.fields,
                                                                                             'status') else 'Unknown',
                        'priority': getattr(issue.fields.priority, 'name', 'None') if hasattr(issue.fields,
                                                                                              'priority') else 'None',
                        'type': getattr(issue.fields.issuetype, 'name', 'Unknown') if hasattr(issue.fields,
                                                                                              'issuetype') else 'Unknown',
                        'components': [comp.name for comp in getattr(issue.fields, 'components', [])] if hasattr(
                            issue.fields, 'components') else [],
                        'labels': getattr(issue.fields, 'labels', []) or [],
                        'created': str(getattr(issue.fields, 'created', '')) or '',
                        'updated': str(getattr(issue.fields, 'updated', '')) or ''
                    }
                    parsed_issues.append(issue_data)
                except Exception as parse_error:
                    logger.warning(f"{log_prefix} Failed to parse issue {issue.key}: {parse_error}")
                    continue

            total_issues = len(parsed_issues)
            update_mcp_stats('successful_fetches')
            update_mcp_stats('total_issues_fetched', total_issues)

            logger.info(f"{log_prefix} Successfully fetched {total_issues} issues from {config.PROJECT_KEY}")

            return {
                'success': True,
                'issues': parsed_issues,
                'total_issues': total_issues,
                'project_key': config.PROJECT_KEY,
                'fetched_at': datetime.now().isoformat()
            }

    except JIRAError as jira_error:
        error_msg = f"JIRA API error: {str(jira_error)} (status: {jira_error.status_code if hasattr(jira_error, 'status_code') else 'N/A'})"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('failed_fetches')
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg,
            'issues': []
        }
    except Exception as e:
        error_msg = f"Unexpected error fetching ALL JIRA issues: {str(e)}"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('failed_fetches')
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg,
            'issues': []
        }


def get_todo_issues_mcp_tool(thread_id: str) -> Dict[str, Any]:
    """
    Fetch only "To Do" issues from the configured JIRA project for code generation.

    Args:
        thread_id: Thread identifier for logging

    Returns:
        Dict with 'success', 'issues' (list of parsed issue dicts), or 'error'
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_prefix = f"[{timestamp}] [MCP-JIRA-TODO] [{thread_id}]"

    update_mcp_stats('todo_fetches')

    if not all([config.JIRA_SERVER, config.JIRA_EMAIL, config.JIRA_TOKEN, config.PROJECT_KEY]):
        error_msg = "JIRA configuration incomplete (server, email, token, or project_key missing)"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('failed_fetches')
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg,
            'issues': []
        }

    try:
        with jira_lock:
            logger.info(f"{log_prefix} Connecting to JIRA server: {config.JIRA_SERVER}")
            jira = get_jira_client()

            logger.info(f"{log_prefix} Fetching TODO issues for project: {config.PROJECT_KEY}")
            jql = f'project = "{config.PROJECT_KEY}" AND status = "To Do" ORDER BY created ASC'

            issues = jira.search_issues(
                jql,
                maxResults=1000,  # Adjust based on project size
                fields="key,summary,description,status,priority,issuetype,components,labels,created,updated"
            )

            parsed_issues: List[Dict[str, Any]] = []
            for issue in issues:
                try:
                    issue_data = {
                        'key': issue.key,
                        'summary': getattr(issue.fields, 'summary', '') or '',
                        'description': getattr(issue.fields, 'description', '') or '',
                        'status': getattr(issue.fields.status, 'name', 'Unknown') if hasattr(issue.fields,
                                                                                             'status') else 'Unknown',
                        'priority': getattr(issue.fields.priority, 'name', 'None') if hasattr(issue.fields,
                                                                                              'priority') else 'None',
                        'type': getattr(issue.fields.issuetype, 'name', 'Unknown') if hasattr(issue.fields,
                                                                                              'issuetype') else 'Unknown',
                        'components': [comp.name for comp in getattr(issue.fields, 'components', [])] if hasattr(
                            issue.fields, 'components') else [],
                        'labels': getattr(issue.fields, 'labels', []) or [],
                        'created': str(getattr(issue.fields, 'created', '')) or '',
                        'updated': str(getattr(issue.fields, 'updated', '')) or ''
                    }
                    parsed_issues.append(issue_data)
                except Exception as parse_error:
                    logger.warning(f"{log_prefix} Failed to parse issue {issue.key}: {parse_error}")
                    continue

            total_issues = len(parsed_issues)
            update_mcp_stats('successful_fetches')
            update_mcp_stats('total_issues_fetched', total_issues)

            logger.info(f"{log_prefix} Successfully fetched {total_issues} TODO issues from {config.PROJECT_KEY}")

            return {
                'success': True,
                'issues': parsed_issues,
                'total_issues': total_issues,
                'project_key': config.PROJECT_KEY,
                'fetched_at': datetime.now().isoformat()
            }

    except JIRAError as jira_error:
        error_msg = f"JIRA API error: {str(jira_error)} (status: {jira_error.status_code if hasattr(jira_error, 'status_code') else 'N/A'})"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('failed_fetches')
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg,
            'issues': []
        }
    except Exception as e:
        error_msg = f"Unexpected error fetching TODO JIRA issues: {str(e)}"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('failed_fetches')
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg,
            'issues': []
        }


def transition_issue(issue_key: str, transition_name: str, thread_id: str = "unknown") -> bool:
    """
    Transition a JIRA issue to a new status.

    Args:
        issue_key: JIRA issue key
        transition_name: Name of the transition (e.g., 'Start Progress', 'Done')
        thread_id: Thread identifier for logging

    Returns:
        True if successful, False otherwise
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_prefix = f"[{timestamp}] [JIRA-TRANSITION] [{thread_id}]"

    try:
        with jira_lock:
            jira = get_jira_client()
            transitions = jira.transitions(issue_key)
            transition_id = next((t['id'] for t in transitions if t['name'].lower() == transition_name.lower()), None)

            if transition_id:
                jira.transition_issue(issue_key, transition_id)
                logger.info(f"{log_prefix} Successfully transitioned {issue_key} to {transition_name}")
                return True
            else:
                logger.warning(f"{log_prefix} Transition '{transition_name}' not available for {issue_key}")
                return False

    except Exception as e:
        logger.error(f"{log_prefix} Failed to transition {issue_key}: {str(e)}")
        return False


def get_mcp_stats() -> Dict[str, Any]:
    """Get MCP JIRA tool statistics"""
    with stats_lock:
        return {
            "tool_type": "mcp_jira_client",
            "version": "1.1",  # Updated with TODO fetch
            "timestamp": datetime.now().isoformat(),
            "config": {
                "server": config.JIRA_SERVER,
                "project_key": config.PROJECT_KEY,
                "has_credentials": bool(config.JIRA_EMAIL and config.JIRA_TOKEN)
            },
            "stats": dict(mcp_stats),
            "features": [
                "complete_issues_fetch",
                "todo_issues_fetch",
                "jira_client_creation",
                "parsed_issue_format",
                "thread_safe_operations",
                "comprehensive_logging",
                "statistics_tracking",
                "error_handling"
            ]
        }


if __name__ == "__main__":
    # Test the MCP tools
    test_all = get_project_issues_mcp_tool("TEST-THREAD")
    print(f"Test Test Fetch: Success={test_all['success']}, Issues={len(test_all.get('issues', []))}")

    test_todo = get_todo_issues_mcp_tool("TEST-THREAD")
    print(f"Test TODO Fetch: Success={test_todo['success']}, Issues={len(test_todo.get('issues', []))}")

    try:
        client = get_jira_client()
        print("JIRA Client created successfully")
    except Exception as e:
        print(f"JIRA Client error: {e}")

    print(f"MCP Stats: {get_mcp_stats()}")