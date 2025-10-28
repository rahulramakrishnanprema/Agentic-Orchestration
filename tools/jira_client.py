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
from typing import Dict, Any, List
from datetime import datetime
from threading import Lock
from jira import JIRA, JIRAError

from config.settings import config


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
    'project_creations': 0,
    'issue_creations': 0,
    'errors': 0
}

stats_lock = Lock()


def update_mcp_stats(key: str, value: int = 1) -> None:
    """Thread-safe statistics update"""
    with stats_lock:
        if key in mcp_stats:
            mcp_stats[key] += value


def extract_text_from_adf(adf_content: dict) -> str:
    """
    Extract plain text from Atlassian Document Format (ADF).
    ADF is a JSON structure used by newer Jira instances.

    Args:
        adf_content: Dictionary containing ADF structure

    Returns:
        Plain text extracted from ADF
    """
    if not isinstance(adf_content, dict):
        return str(adf_content)

    text_parts = []

    def extract_text_recursive(node):
        """Recursively extract text from ADF nodes"""
        if isinstance(node, dict):
            # Extract text from text nodes
            if node.get('type') == 'text':
                text_parts.append(node.get('text', ''))

            # Process content array
            if 'content' in node:
                for child in node['content']:
                    extract_text_recursive(child)

            # Add spacing for certain node types
            if node.get('type') in ['paragraph', 'heading', 'listItem']:
                text_parts.append('\n')

        elif isinstance(node, list):
            for item in node:
                extract_text_recursive(item)

    extract_text_recursive(adf_content)

    # Join and clean up the text
    result = ''.join(text_parts).strip()
    # Remove excessive newlines
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')

    return result


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
                    # Extract description with proper handling for different Jira formats
                    raw_description = getattr(issue.fields, 'description', None)

                    # DEBUG: Log raw description to see what format Jira is returning
                    logger.info(f"{log_prefix} DEBUG - Issue {issue.key} raw description type: {type(raw_description)}")
                    logger.info(f"{log_prefix} DEBUG - Issue {issue.key} raw description: {str(raw_description)[:200] if raw_description else 'NULL/NONE'}")

                    # Handle different Jira description formats
                    description = ''
                    if raw_description is None:
                        description = ''
                    elif isinstance(raw_description, str):
                        # Plain text description
                        description = raw_description
                    elif isinstance(raw_description, dict):
                        # Atlassian Document Format (ADF) - extract text content
                        description = extract_text_from_adf(raw_description)
                        logger.info(f"{log_prefix} DEBUG - Extracted from ADF: {description[:200]}")
                    else:
                        # Fallback: convert to string
                        description = str(raw_description)

                    issue_data = {
                        'key': issue.key,
                        'summary': getattr(issue.fields, 'summary', '') or '',
                        'description': description,
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
                    # Extract description with proper handling for different Jira formats
                    raw_description = getattr(issue.fields, 'description', None)

                    # Handle different Jira description formats
                    description = ''
                    if raw_description is None:
                        description = ''
                    elif isinstance(raw_description, str):
                        # Plain text description
                        description = raw_description
                    elif isinstance(raw_description, dict):
                        # Atlassian Document Format (ADF) - extract text content
                        description = extract_text_from_adf(raw_description)
                    else:
                        # Fallback: convert to string
                        description = str(raw_description)

                    issue_data = {
                        'key': issue.key,
                        'summary': getattr(issue.fields, 'summary', '') or '',
                        'description': description,
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


def create_jira_project_mcp_tool(project_name: str, project_key: str, description: str, thread_id: str) -> Dict[str, Any]:
    """
    Create a new JIRA project using MCP protocol.

    Args:
        project_name: Name of the project (e.g., "E-commerce Platform")
        project_key: Project key (e.g., "ECOM") - must be uppercase, 2-10 chars
        description: Project description
        thread_id: Thread identifier for logging

    Returns:
        Dict with 'success', 'project_key', 'project_id', or 'error'
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_prefix = f"[{timestamp}] [MCP-JIRA-CREATE-PROJECT] [{thread_id}]"

    update_mcp_stats('project_creations')

    try:
        with jira_lock:
            logger.info(f"{log_prefix} Creating new JIRA project: {project_name} ({project_key})")
            jira = get_jira_client()

            # Get current user's account ID
            logger.info(f"{log_prefix} Getting current user account ID...")
            current_user = jira.myself()
            account_id = current_user.get('accountId')
            logger.info(f"{log_prefix} Current user account ID: {account_id}")

            # Use MCP protocol - Direct REST API call for JIRA Cloud
            logger.info(f"{log_prefix} Creating project via MCP REST API...")

            project_data = {
                'key': project_key.upper(),
                'name': project_name,
                'projectTypeKey': 'software',  # Software project type
                'description': description,
                'leadAccountId': account_id  # Use current user's account ID
            }

            # Make direct API call using MCP
            response = jira._session.post(
                f"{jira._options['server']}/rest/api/3/project",
                json=project_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                project_id = result.get('id', result.get('key'))
                project_key_returned = result.get('key')

                logger.info(f"{log_prefix} Successfully created project {project_key_returned}: {project_id}")

                return {
                    'success': True,
                    'project_key': project_key_returned.upper(),
                    'project_id': str(project_id),
                    'project_name': project_name,
                    'created_at': datetime.now().isoformat()
                }
            else:
                error_text = response.text
                logger.error(f"{log_prefix} API returned status {response.status_code}: {error_text}")
                raise JIRAError(status_code=response.status_code, text=error_text)

    except Exception as e:
        error_msg = f"Failed to create JIRA project: {str(e)}"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg
        }


def create_jira_issue_mcp_tool(project_key: str, summary: str, description: str,
                               issue_type: str = "Task", thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Create a new JIRA issue/subtask using MCP protocol.

    Args:
        project_key: Project key where issue should be created
        summary: Issue summary/title
        description: Issue description
        issue_type: Type of issue (Task, Story, Bug, etc.)
        thread_id: Thread identifier for logging

    Returns:
        Dict with 'success', 'issue_key', 'issue_id', or 'error'
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_prefix = f"[{timestamp}] [MCP-JIRA-CREATE-ISSUE] [{thread_id}]"

    update_mcp_stats('issue_creations')

    try:
        with jira_lock:
            logger.info(f"{log_prefix} Creating new JIRA issue in {project_key}: {summary}")
            jira = get_jira_client()

            # Create issue
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }

            new_issue = jira.create_issue(fields=issue_dict)

            logger.info(f"{log_prefix} Successfully created issue {new_issue.key}: {new_issue.id}")

            return {
                'success': True,
                'issue_key': new_issue.key,
                'issue_id': new_issue.id,
                'project_key': project_key,
                'created_at': datetime.now().isoformat()
            }

    except Exception as e:
        error_msg = f"Failed to create JIRA issue: {str(e)}"
        logger.error(f"{log_prefix} {error_msg}")
        update_mcp_stats('errors')
        return {
            'success': False,
            'error': error_msg
        }


def get_mcp_stats() -> Dict[str, Any]:
    """Get MCP JIRA tool statistics"""
    with stats_lock:
        return {
            "tool_type": "mcp_jira_client",
            "version": "1.2",  # Updated with project/issue creation
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
                "error_handling",
                "project_creation",
                "issue_creation"
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