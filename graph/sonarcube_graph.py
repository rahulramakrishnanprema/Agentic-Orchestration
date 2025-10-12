from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import requests
from github import Github
import logging
from datetime import datetime
from pymongo import MongoClient  # If needed for storage, but logic uses instance in node
import os

logger = logging.getLogger(__name__)

class SonarQubeState(dict):
    thread_id: str
    latest_pr: Dict[str, Any]
    issues: List[Dict[str, Any]]
    measures: Dict[str, Any]
    pr_files: List[str]
    overall_score: float
    all_issues: List[Dict[str, Any]]
    success: bool
    error: Optional[str]
    processing_time: float

def _node_select_latest_pr(state: SonarQubeState) -> SonarQubeState:
    try:
        gh = Github(os.getenv("GITHUB_TOKEN"))
        repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
        prs = repo.get_pulls(state='open', sort='updated', direction='desc')
        if not prs:
            state['error'] = "No open pull requests found"
            return state
        latest = prs[0]
        state['latest_pr'] = {
            'key': str(latest.number),
            'title': latest.title,
            'branch': latest.head.ref,
            'updatedAt': latest.updated_at.isoformat()
        }
        print(f"Selected PR #{latest.number}: {latest.title}")
    except Exception as e:
        state['error'] = f"Failed to select latest PR: {e}"
    return state

def _node_fetch_issues(state: SonarQubeState) -> SonarQubeState:
    if state.get('error'):
        return state
    pr_key = state['latest_pr']['key']
    issues = []
    page = 1
    sonar_host = os.getenv("SONAR_HOST_URL").strip().strip('"').rstrip('/')
    sonar_token = os.getenv("SONAR_TOKEN")
    sonar_project_key = os.getenv("SONAR_PROJECT_KEY")
    headers = {
        "Authorization": f"Bearer {sonar_token}",
        "Content-Type": "application/json"
    }
    while True:
        url = f"{sonar_host}/api/issues/search"
        params = {
            'componentKeys': sonar_project_key,
            'pullRequest': pr_key,
            'ps': 100,
            'p': page,
            'resolved': 'false'
        }
        try:
            print(f"Fetching issues: {url} with params: {params}")
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            issues.extend(data.get('issues', []))
            total = data.get('total', 0)
            if page * 100 >= total:
                break
            page += 1
        except Exception as e:
            state['error'] = f"Issues fetch failed: {e}"
            return state
    state['issues'] = issues
    print(f"Found {len(issues)} issues")
    return state

def _node_fetch_measures(state: SonarQubeState) -> SonarQubeState:
    if state.get('error'):
        return state
    sonar_host = os.getenv("SONAR_HOST_URL").strip().strip('"').rstrip('/')
    sonar_token = os.getenv("SONAR_TOKEN")
    sonar_project_key = os.getenv("SONAR_PROJECT_KEY")
    headers = {
        "Authorization": f"Bearer {sonar_token}",
        "Content-Type": "application/json"
    }
    url = f"{sonar_host}/api/measures/component"
    metrics = [
        'alert_status', 'bugs', 'vulnerabilities', 'code_smells',
        'security_hotspots', 'sqale_rating', 'reliability_rating',
        'security_rating', 'coverage', 'duplicated_lines_density'
    ]
    try:
        params = {
            'component': sonar_project_key,
            'metricKeys': ','.join(metrics)
        }
        print(f"Fetching project-wide measures: {url} with params: {params}")
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        comp = resp.json().get('component', {})
        measures = {m['metric']: m.get('value', '0') for m in comp.get('measures', [])}

        # Attach PR-specific issue count so we can factor it in later
        measures['pr_issue_count'] = str(len(state.get('issues', [])))

        state['measures'] = measures
        print(f"Retrieved {len(measures)} measures (plus PR issues count)")

    except Exception as e:
        state['error'] = f"Measures fetch failed: {e}"
    return state

def _node_fetch_pr_files(state: SonarQubeState) -> SonarQubeState:
    if state.get('error'):
        return state
    try:
        gh = Github(os.getenv("GITHUB_TOKEN"))
        repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
        pr = repo.get_pull(int(state['latest_pr']['key']))
        commits = list(pr.get_commits())
        if not commits:
            state['error'] = "No commits found in PR"
            return state
        last_sha = commits[-1].sha
        commit = repo.get_commit(last_sha)
        state['pr_files'] = [f.filename for f in commit.files]
        print(f"Found {len(state['pr_files'])} files in last commit")
    except Exception as e:
        state['error'] = f"Failed to fetch last-commit files: {e}"
    return state

def _node_calculate_score(state: SonarQubeState) -> SonarQubeState:
    if state.get('error'):
        return state
    m = state['measures']
    gate = m.get('alert_status', 'ERROR')
    gate_score = 100 if gate == 'OK' else 70 if gate == 'WARN' else 0
    ratings = [(6 - float(m.get(r, '5'))) * 20 for r in
               ('sqale_rating', 'reliability_rating', 'security_rating')]
    bugs = int(m.get('bugs', 0))
    vul = int(m.get('vulnerabilities', 0))
    smells = int(m.get('code_smells', 0))
    hotspots = int(m.get('security_hotspots', 0))
    penalty = min(50, bugs * 10 + vul * 15 + smells * 2 + hotspots * 5)
    cov = min(100, float(m.get('coverage', 0)))
    dup = min(20, float(m.get('duplicated_lines_density', 0)))
    base = sum(ratings) / len(ratings) if ratings else 50
    final = base * 0.5 + gate_score * 0.3 + cov * 0.2 - penalty - dup
    state['overall_score'] = round(max(0, min(100, final)), 1)
    state['all_issues'] = state['issues']
    state['success'] = True
    return state

def _node_store_results(state: SonarQubeState) -> SonarQubeState:
    if state.get('error'):
        return state
    mongo_conn_str = os.getenv("MONGODB_CONNECTION_STRING")  # Adapted from config
    mongo_db_name = os.getenv("MONGODB_DATABASE", 'code_review')  # Adapted
    if not mongo_conn_str:
        return state
    try:
        mongo_client = MongoClient(mongo_conn_str)
        mongo_db = mongo_client[mongo_db_name]
        mongo_collection = mongo_db['sonarqube_results']
        document = {
            "thread_id": state["thread_id"],
            "pr_key": state["latest_pr"].get("key"),
            "pr_title": state["latest_pr"].get("title"),
            "overall_score": state["overall_score"],
            "issues": state["all_issues"],
            "measures": state["measures"],
            "pr_files": state["pr_files"],
            "timestamp": datetime.now().isoformat()
        }
        mongo_collection.insert_one(document)
        logger.info("Stored SonarQube results in MongoDB")
    except Exception as e:
        logger.error(f"Failed to store SonarQube results in MongoDB: {e}")
    return state

def _node_print_results(state: SonarQubeState) -> SonarQubeState:
    print("\n" + "=" * 60)
    print("SonarQube Analysis Results")
    print("=" * 60)
    pr = state['latest_pr']
    print(f"PR Number: #{pr.get('key', 'N/A')}")
    print(f"PR Title:  {pr.get('title', 'N/A')}")
    print(f"Branch:    {pr.get('branch', 'N/A')}")
    print(f"Updated At:{pr.get('updatedAt', 'N/A')}\n")
    print(f"Files in last commit ({len(state['pr_files'])}):")
    for f in state['pr_files'][:20]:
        print(f"  - {f}")
    if len(state['pr_files']) > 20:
        print(f"  ... and {len(state['pr_files']) - 20} more files")
    print(f"\nOverall Quality Score: {state['overall_score']}/100")
    print(f"Quality Gate: {state['measures'].get('alert_status', 'UNKNOWN')}\n")
    print("Key Metrics:")
    for k in ['bugs', 'vulnerabilities', 'code_smells',
              'security_hotspots', 'coverage', 'duplicated_lines_density']:
        val = state['measures'].get(k, '0')
        suffix = '%' if k in ['coverage', 'duplicated_lines_density'] and val != '0' else ''
        print(f"  {k.replace('_', ' ').title()}: {val}{suffix}")

    print(f"\nIssues Found: {len(state['all_issues'])}")
    if state['all_issues']:
        by_sev = {}
        for issue in state['all_issues']:
            sev = issue.get('severity', 'UNKNOWN')
            by_sev[sev] = by_sev.get(sev, 0) + 1
        print("  By Severity:")
        for sev, count in sorted(by_sev.items()):
            print(f"    {sev}: {count}")

        # Print detailed issues
        print("\n" + "-" * 60)
        print("DETAILED ISSUES:")
        print("-" * 60)

        # Group issues by severity for better organization
        severity_order = ['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO']
        for severity in severity_order:
            severity_issues = [issue for issue in state['all_issues'] if issue.get('severity') == severity]
            if severity_issues:
                print(f"\n{severity} ISSUES ({len(severity_issues)}):")
                print("-" * 40)
                for i, issue in enumerate(severity_issues, 1):
                    print(f"{i}. {issue.get('message', 'No message')}")
                    print(f"   Rule: {issue.get('rule', 'Unknown')}")
                    component = issue.get('component', 'Unknown')
                    if component and ':' in component:
                        component = component.split(':')[-1]
                    print(f"   Component: {component}")
                    if issue.get('line'):
                        print(f"   Line: {issue.get('line')}")
                    if issue.get('type'):
                        print(f"   Type: {issue.get('type')}")
                    if issue.get('effort'):
                        print(f"   Effort: {issue.get('effort')}")
                    if issue.get('debt'):
                        print(f"   Technical Debt: {issue.get('debt')}")
                    if issue.get('tags'):
                        print(f"   Tags: {', '.join(issue.get('tags', []))}")
                    print()

    print(f"Analysis completed in {state.get('processing_time', 0):.2f} seconds")
    print("=" * 60)
    return state

def build_sonarcube_graph():
    wf = StateGraph(SonarQubeState)
    wf.add_node("select_latest_pr", _node_select_latest_pr)
    wf.add_node("fetch_issues", _node_fetch_issues)
    wf.add_node("fetch_measures", _node_fetch_measures)
    wf.add_node("fetch_pr_files", _node_fetch_pr_files)
    wf.add_node("calculate_score", _node_calculate_score)
    wf.add_node("store_results", _node_store_results)  # NEW: Store to MongoDB
    wf.add_node("print_results", _node_print_results)

    wf.set_entry_point("select_latest_pr")
    wf.add_edge("select_latest_pr", "fetch_issues")
    wf.add_edge("fetch_issues", "fetch_measures")
    wf.add_edge("fetch_measures", "fetch_pr_files")
    wf.add_edge("fetch_pr_files", "calculate_score")
    wf.add_edge("calculate_score", "store_results")  # NEW
    wf.add_edge("store_results", "print_results")
    wf.add_edge("print_results", END)

    return wf.compile(checkpointer=MemorySaver())