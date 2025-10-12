"""
Simplified Reviewer Tools - Reduced Code with Full Functionality
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import Lock
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError
import subprocess
import tempfile
import sys
from io import StringIO
from dotenv import load_dotenv
from tools.prompt_loader import PromptLoader

from config.settings import config as app_config
from services.llm_service import call_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Shared resources and locks
stats_lock = Lock()
mongodb_lock = Lock()

# Global configuration (initialized once)
config = None
prompt_loader = PromptLoader("prompts")
llm_instance = None
mongo_client = None
mongo_collection = None
knowledge_base = {}

# Statistics tracking
tool_stats = {
    'knowledge_base_calls': 0, 'completeness_analyses': 0, 'security_analyses': 0,
    'standards_analyses': 0, 'score_calculations': 0, 'mongodb_operations': 0,
    'file_formatting_calls': 0, 'total_tokens': 0, 'errors': 0, 'pylint_analyses': 0
}


# Pydantic Models (preserved)
class ReviewResult(BaseModel):
    """Structured review result for a single dimension."""
    score: float = Field(description="Review score from 0-100", ge=0, le=100)
    mistakes: List[str] = Field(description="List of identified issues and improvement suggestions")
    reasoning: str = Field(description="Explanation for the score", default="")


class ComprehensiveReviewResult(BaseModel):
    """Complete review result with all dimensions."""
    success: bool
    overall_score: float
    threshold: float
    approved: bool
    completeness_score: float
    security_score: float
    standards_score: float
    issues: List[str]
    tokens_used: int
    mongodb_stored: bool


# Initialization functions
def initialize_reviewer_tools(app_config, app_prompt_loader, app_llm):
    """Initialize shared resources for all reviewer tools"""
    global config, prompt_loader, llm_instance, knowledge_base, mongo_client, mongo_collection

    config = app_config
    prompt_loader = app_prompt_loader or PromptLoader("prompts")
    llm_instance = app_llm

    # Load knowledge base
    _load_knowledge_base()

    # Initialize MongoDB if enabled
    if getattr(config, 'MONGODB_ENABLED', True):
        _initialize_mongodb()

    logger.info("Simplified reviewer tools initialized successfully")


def _load_knowledge_base():
    """Load knowledge base files once at startup"""
    global knowledge_base
    standards_folder = getattr(config, 'STANDARDS_FOLDER', 'standards')

    if not os.path.exists(standards_folder):
        logger.warning(f"Standards folder not found: {standards_folder}")
        return

    try:
        knowledge_base = {}
        for filename in os.listdir(standards_folder):
            if filename.endswith('.md'):
                file_path = os.path.join(standards_folder, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        key = filename[:-3]
                        knowledge_base[key] = content
                        logger.info(f"Loaded knowledge base: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to load {filename}: {e}")

        logger.info(f"Knowledge base loaded: {len(knowledge_base)} files")
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")


def _initialize_mongodb():
    """Initialize MongoDB connection once at startup"""
    global mongo_client, mongo_collection

    try:
        connection_string = config.MONGODB_CONNECTION_STRING
        database_name = config.MONGODB_DATABASE
        collection_name = config.MONGODB_COLLECTION

        mongo_client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            maxPoolSize=10
        )

        server_info = mongo_client.server_info()
        logger.info(f"MongoDB connected - Version: {server_info.get('version', 'Unknown')}")

        mongo_db = mongo_client[database_name]
        mongo_collection = mongo_db[collection_name]

        try:
            mongo_collection.create_index("jira_task")
            mongo_collection.create_index("date")
            mongo_collection.create_index("overall_score")
        except Exception as e:
            logger.warning(f"Could not create MongoDB indexes: {e}")

        logger.info(f"MongoDB ready - Collection: {collection_name}")
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        mongo_client = None
        mongo_collection = None


def parse_llm_result(content: str, review_type: str) -> ReviewResult:
    """Shared function to parse LLM results into structured format with robust error handling."""
    try:
        cleaned_content = content.strip()

        if cleaned_content.startswith('```'):
            start = cleaned_content.find('\n')
            end = cleaned_content.rfind('```')
            if start != -1 and end != -1:
                cleaned_content = cleaned_content[start:end].strip()

        if '{' in cleaned_content and '}' in cleaned_content:
            json_start = cleaned_content.find('{')
            json_end = cleaned_content.rfind('}') + 1
            json_str = cleaned_content[json_start:json_end]

            try:
                parsed = json.loads(json_str)

                score = float(parsed.get('score', 75.0))
                mistakes = parsed.get('mistakes', [])
                reasoning = parsed.get('reasoning', '')

                if not isinstance(mistakes, list):
                    mistakes = [str(mistakes)]

                score = max(0.0, min(100.0, score))

                return ReviewResult(
                    score=score,
                    mistakes=mistakes if mistakes else [f"{review_type} review completed"],
                    reasoning=reasoning if reasoning else f"{review_type} analysis performed"
                )

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in {review_type}: {e}")

        logger.warning(f"Could not parse {review_type} result, using defaults")
        return ReviewResult(
            score=75.0,
            mistakes=[f"Could not parse {review_type} review - please check manually"],
            reasoning=f"Automated {review_type} review incomplete"
        )

    except Exception as e:
        logger.error(f"Error parsing {review_type} result: {e}")
        return ReviewResult(
            score=70.0,
            mistakes=[f"Error in {review_type} review: {str(e)}"],
            reasoning="Review encountered an error"
        )


# Tool definitions using @tool decorator
@tool
def get_knowledge_base_content(operation: str, file_types: List[str] = None) -> Dict[str, Any]:
    """
    Get content from knowledge base for coding standards and security guidelines.

    Args:
        operation: Type of operation (get_standards_content, get_security_guidelines, get_language_standards)
        file_types: List of file types to get standards for
    """
    try:
        with stats_lock:
            tool_stats['knowledge_base_calls'] += 1

        file_types = file_types or []

        if operation == "get_standards_content":
            standards_content = []

            # Always include security guidelines
            if 'security_guidelines' in knowledge_base:
                standards_content.append("SECURITY GUIDELINES:\n" + knowledge_base['security_guidelines'])

            # Include language-specific standards
            for file_type in file_types:
                if file_type in knowledge_base:
                    standards_content.append(f"{file_type.upper()} STANDARDS:\n" + knowledge_base[file_type])

            # Fallback to general coding standards
            if len(standards_content) == 1 and 'coding_standards' in knowledge_base:
                standards_content.append("GENERAL CODING STANDARDS:\n" + knowledge_base['coding_standards'])

            if not standards_content:
                content = "No specific standards found in knowledge base. Using general review principles."
            else:
                content = "\n\n".join(standards_content)

            return {"success": True, "content": content, "files_used": len(knowledge_base)}

        elif operation == "get_security_guidelines":
            security_content = knowledge_base.get('security_guidelines', 'Use general security best practices')
            return {"success": True, "content": security_content}

        elif operation == "get_language_standards":
            standards = []
            for file_type in file_types:
                if file_type in knowledge_base:
                    standards.append(f"{file_type.upper()} STANDARDS:\n{knowledge_base[file_type]}")

            if not standards and 'coding_standards' in knowledge_base:
                standards.append(f"GENERAL STANDARDS:\n{knowledge_base['coding_standards']}")

            content = "\n\n".join(standards) if standards else "Use general coding best practices"
            return {"success": True, "content": content}

        else:
            return {"success": False, "error": "Invalid operation"}

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e)}


@tool
def analyze_code_completeness(issue_key: str, project_description: str, files_content: str,
                              standards_content: str, thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Analyze code completeness against requirements using LLM.

    Args:
        issue_key: Jira issue identifier
        project_description: Description of the project
        files_content: Formatted content of all files
        standards_content: Standards content from knowledge base
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['completeness_analyses'] += 1

        logger.info(f"[{thread_id}] Analyzing completeness for {issue_key}")

        # Setup prompt - use PromptLoader.format() method correctly
        completeness_prompt = prompt_loader.format(
            "reviewer_completeness_analysis",
            issue_key=issue_key,
            project_description=project_description,
            files_content=files_content,
            standards_content=standards_content
        )

        content, tokens = call_llm(completeness_prompt, agent_name="reviewer")

        logger.info(f"[{thread_id}] LLM returned {len(content)} characters for completeness analysis")
        logger.debug(f"[{thread_id}] LLM response preview: {content[:200]}")

        # Parse result
        parsed_result = parse_llm_result(content, "completeness")

        logger.info(f"[{thread_id}] Completeness score: {parsed_result.score}, mistakes: {len(parsed_result.mistakes)}")

        return {
            "success": True,
            "score": parsed_result.score,
            "mistakes": parsed_result.mistakes,
            "reasoning": parsed_result.reasoning,
            "tokens_used": tokens
        }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Completeness analysis failed: {str(e)}")
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def analyze_code_security(issue_key: str, files_content: str, security_standards: str,
                          thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Analyze code security vulnerabilities using LLM.

    Args:
        issue_key: Jira issue identifier
        files_content: Formatted content of all files
        security_standards: Security standards from knowledge base
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['security_analyses'] += 1

        logger.info(f"[{thread_id}] Analyzing security for {issue_key}")

        # Setup prompt - use PromptLoader.format() method consistently
        security_prompt = prompt_loader.format(
            "reviewer_security_analysis",
            issue_key=issue_key,
            files_content=files_content,
            security_standards=security_standards
        )

        content, tokens = call_llm(security_prompt, agent_name="reviewer")

        logger.info(f"[{thread_id}] LLM returned {len(content)} characters for security analysis")
        logger.debug(f"[{thread_id}] LLM response preview: {content[:200]}")

        # Parse result
        parsed_result = parse_llm_result(content, "security")

        logger.info(f"[{thread_id}] Security score: {parsed_result.score}, mistakes: {len(parsed_result.mistakes)}")

        return {
            "success": True,
            "score": parsed_result.score,
            "mistakes": parsed_result.mistakes,
            "reasoning": parsed_result.reasoning,
            "tokens_used": tokens
        }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Security analysis failed: {str(e)}")
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def analyze_coding_standards(file_types: List[str], files_content: str, language_standards: str,
                             thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Analyze code against coding standards using LLM.

    Args:
        file_types: List of file types being analyzed
        files_content: Formatted content of all files
        language_standards: Language-specific standards from knowledge base
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['standards_analyses'] += 1

        logger.info(f"[{thread_id}] Analyzing standards for {', '.join(file_types)}")

        # Setup prompt - use PromptLoader.format() method correctly
        standards_prompt = prompt_loader.format(
            "reviewer_standards_analysis",
            file_types=", ".join(file_types),
            files_content=files_content,
            language_standards=language_standards
        )

        content, tokens = call_llm(standards_prompt, agent_name="reviewer")

        logger.info(f"[{thread_id}] LLM returned {len(content)} characters for standards analysis")
        logger.debug(f"[{thread_id}] LLM response preview: {content[:200]}")

        # Parse result
        parsed_result = parse_llm_result(content, "standards")

        logger.info(f"[{thread_id}] Standards score: {parsed_result.score}, mistakes: {len(parsed_result.mistakes)}")

        return {
            "success": True,
            "score": parsed_result.score,
            "mistakes": parsed_result.mistakes,
            "reasoning": parsed_result.reasoning,
            "tokens_used": tokens
        }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Standards analysis failed: {str(e)}")
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def calculate_review_scores(completeness_score: float, security_score: float, standards_score: float,
                            custom_threshold: Optional[float] = None) -> Dict[str, Any]:
    """
    Calculate weighted review scores and determine approval status.

    Args:
        completeness_score: Completeness analysis score (0-100)
        security_score: Security analysis score (0-100)
        standards_score: Standards analysis score (0-100)
        custom_threshold: Optional custom threshold (default from config)
    """
    try:
        with stats_lock:
            tool_stats['score_calculations'] += 1

        # Get threshold
        threshold = custom_threshold if custom_threshold is not None else getattr(config, 'REVIEW_THRESHOLD', 70.0)

        # Define weights
        weights = {'completeness': 0.4, 'security': 0.4, 'standards': 0.2}

        # Calculate weighted overall score
        overall_score = (
                completeness_score * weights['completeness'] +
                security_score * weights['security'] +
                standards_score * weights['standards']
        )

        # Determine approval
        approved = overall_score >= threshold

        return {
            "success": True,
            "overall_score": round(overall_score, 1),
            "threshold": threshold,
            "approved": approved,
            "weights_used": weights,
            "status": "APPROVED" if approved else "NEEDS_IMPROVEMENT"
        }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e)}


@tool
def store_review_in_mongodb(issue_key: str, issues: List[str], completeness_score: float,
                            security_score: float, standards_score: float, overall_score: float,
                            iteration: int, thread_id: str, tokens_used: int = 0) -> Dict[str, Any]:
    """
    Store comprehensive review data in MongoDB.

    Args:
        issue_key: Jira issue key
        issues: List of all identified issues
        completeness_score: Completeness analysis score
        security_score: Security analysis score
        standards_score: Standards analysis score
        overall_score: Calculated overall score
        iteration: Review iteration number
        thread_id: Thread identifier
        tokens_used: Tokens used in review
    """
    try:
        with stats_lock:
            tool_stats['mongodb_operations'] += 1

        if mongo_collection is None:
            return {"success": False, "error": "MongoDB not available"}

        with mongodb_lock:
            agent_id = "001" if iteration == 1 else "003"
            local_time = datetime.now()
            # Create review document
            review_document = {
                "agent_id": agent_id,
                "date": local_time,
                "jira_task": issue_key,
                "iteration": iteration,
                "thread_id": thread_id,
                "llm": getattr(config, 'ASSEMBLER_LLM_MODEL', 'unknown'),
                "model_temperature": 0.1,
                "overall_score": round(overall_score, 1),
                "total_mistakes": len(issues),
                "all_mistake_notes": issues,
                "review_timestamp": local_time.isoformat(),
                "scores_breakdown": {
                    "completeness": round(completeness_score, 1),
                    "security": round(security_score, 1),
                    "standards": round(standards_score, 1),
                    "overall": round(overall_score, 1)
                },
                "tokens_used": tokens_used
            }

            result = mongo_collection.insert_one(review_document)

            return {
                "success": True,
                "document_id": str(result.inserted_id),
                "agent_id": agent_id,
                "timestamp": local_time.isoformat()
            }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e)}


@tool
def format_files_for_review(files: Dict[str, str]) -> Dict[str, Any]:
    """
    Format files dictionary into structured content for LLM analysis.

    Args:
        files: Dictionary mapping filenames to file contents
    """
    try:
        with stats_lock:
            tool_stats['file_formatting_calls'] += 1

        formatted_files = []
        total_chars = 0

        for filename, content in files.items():
            formatted_content = f"\n=== {filename} ===\n{content}\n"
            formatted_files.append(formatted_content)
            total_chars += len(formatted_content)

        result = "\n".join(formatted_files)

        return {
            "success": True,
            "formatted_content": result,
            "files_processed": len(files),
            "total_characters": total_chars,
            "tokens_used": 0  # NEW: Explicit 0
        }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def analyze_python_code_with_pylint(files_content: Dict[str, str], thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Analyze Python code using Pylint with LLM-powered scoring for comprehensive assessment.
    Uses LLM to intelligently evaluate Pylint issues and provide meaningful scores.

    Args:
        files_content: Dictionary mapping filenames to file contents
        thread_id: Thread identifier for logging
    """
    try:
        import subprocess
        import tempfile
        import os
        import json
        from io import StringIO
        import sys
        from pylint.lint import Run
        from pylint.reporters import JSONReporter

        with stats_lock:
            tool_stats['pylint_analyses'] += 1

        logger.info(f"[{thread_id}] Running Pylint analysis on Python files with LLM scoring")

        pylint_results = {}
        all_issues = []
        all_issues_json = []
        total_files = 0

        for filename, content in files_content.items():
            # Only analyze Python files
            if not filename.endswith('.py'):
                continue

            total_files += 1

            # Create temporary file for Pylint analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # Capture Pylint output
                pylint_output = StringIO()
                reporter = JSONReporter(pylint_output)

                # Run Pylint without any filters
                pylint_args = [
                    temp_path,
                    '--output-format=json',
                    '--reports=yes',
                    '--score=yes'
                ]

                # Run Pylint and capture results
                run = Run(pylint_args, reporter=reporter, exit=False)

                # Parse results
                pylint_output.seek(0)
                output_content = pylint_output.getvalue()
                issues = json.loads(output_content) if output_content.strip() else []

                # Count issues by type
                error_count = len([msg for msg in issues if msg['type'] == 'error'])
                warning_count = len([msg for msg in issues if msg['type'] == 'warning'])
                convention_count = len([msg for msg in issues if msg['type'] == 'convention'])
                refactor_count = len([msg for msg in issues if msg['type'] == 'refactor'])

                # Format issues for display
                file_issues = []
                for issue in issues:
                    formatted_issue = f"Line {issue['line']}: [{issue['type'].upper()}] {issue['message']} ({issue['symbol']})"
                    file_issues.append(formatted_issue)
                    all_issues.append(f"{filename} - {formatted_issue}")

                    # Collect for LLM analysis
                    all_issues_json.append({
                        "file": filename,
                        "line": issue['line'],
                        "type": issue['type'],
                        "message": issue['message'],
                        "symbol": issue['symbol']
                    })

                pylint_results[filename] = {
                    'errors': error_count,
                    'warnings': warning_count,
                    'conventions': convention_count,
                    'refactors': refactor_count,
                    'issues': file_issues,
                    'total_issues': len(issues)
                }

                logger.info(f"[{thread_id}] Pylint found {len(issues)} issues in {filename} (E:{error_count} W:{warning_count} C:{convention_count} R:{refactor_count})")

            except Exception as e:
                logger.error(f"[{thread_id}] Pylint analysis failed for {filename}: {e}")
                pylint_results[filename] = {
                    'errors': 0,
                    'warnings': 0,
                    'conventions': 0,
                    'refactors': 0,
                    'issues': [f"Pylint analysis failed: {str(e)}"],
                    'total_issues': 1
                }

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        # Define unwanted issues to filter
        unwanted_symbols = ["missing-final-newline", "trailing-whitespace", "line-too-long"]
        unwanted_ids = ["C0304", "C0303", "C0301"]

        # Filter issues
        filtered_issues_json = [issue for issue in all_issues_json
                                if issue["symbol"] not in unwanted_symbols
                                and issue["message-id"] not in unwanted_ids]

        # Update all_issues to filtered only
        all_issues = [f"{issue['file']} - Line {issue['line']}: [{issue['type'].upper()}] {issue['message']} ({issue['symbol']})"
                      for issue in filtered_issues_json]

        logger.info(f"[{thread_id}] Filtered Pylint issues: {len(filtered_issues_json)} (from original {len(all_issues_json)})")

        # Use LLM to analyze filtered Pylint issues and calculate intelligent score
        if total_files == 0:
            return {
                "success": True,
                "score": 0.0,
                "pylint_score": 0.0,
                "mistakes": ["No Python files to analyze"],
                "reasoning": "No Python files found in the codebase.",
                "file_results": {},
                "files_analyzed": 0,
                "tokens_used": 0
            }

        if len(filtered_issues_json) == 0:
            logger.info(f"[{thread_id}] No significant issues after filtering - assigning perfect score")
            final_score = 100.0
            reasoning = "No significant issues found after filtering minor style problems (e.g., line length, trailing whitespace, final newline)."
            tokens = 0
        else:
            # Prepare issues for LLM analysis
            issues_json_str = json.dumps(filtered_issues_json, indent=2)

            # Use LLM to score the Pylint results
            pylint_prompt = prompt_loader.format(
                "pylint_score",
                issues_json=issues_json_str
            )

            content, tokens = call_llm(pylint_prompt, agent_name="reviewer")

            logger.info(f"[{thread_id}] LLM returned {len(content)} characters for Pylint scoring")
            logger.debug(f"[{thread_id}] LLM response preview: {content[:200]}")

            # Parse LLM result
            parsed_result = parse_llm_result(content, "pylint")

            final_score = parsed_result.score
            reasoning = parsed_result.reasoning

            logger.info(f"[{thread_id}] LLM-powered Pylint score: {final_score}/100")

        return {
            "success": True,
            "score": final_score,
            "pylint_score": final_score / 10.0,  # Convert to 0-10 scale for compatibility
            "mistakes": all_issues if all_issues else ["No issues found - excellent code quality!"],
            "reasoning": reasoning,
            "file_results": pylint_results,
            "files_analyzed": total_files,
            "tokens_used": tokens
        }

    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Pylint integration failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "score": 0.0,
            "mistakes": [f"Pylint analysis failed: {str(e)}"],
            "tokens_used": 0
        }


def get_reviewer_tools():
    """Get all reviewer tools as a list for LangGraph integration"""
    return [
        get_knowledge_base_content,
        analyze_code_completeness,
        analyze_code_security,
        analyze_coding_standards,
        calculate_review_scores,
        store_review_in_mongodb,
        format_files_for_review,
        analyze_python_code_with_pylint  # NEW TOOL
    ]


def get_reviewer_tools_stats() -> Dict[str, Any]:
    """Get comprehensive statistics from all reviewer tools"""
    with stats_lock:
        return {
            "tool_type": "simplified_reviewer_tools",
            "version": "2.0",
            "code_reduction": "70%",
            "timestamp": datetime.now().isoformat(),
            "total_tools": 8,
            "tools_available": [
                "get_knowledge_base_content",
                "analyze_code_completeness",
                "analyze_code_security",
                "analyze_coding_standards",
                "calculate_review_scores",
                "store_review_in_mongodb",
                "format_files_for_review",
                "analyze_python_code_with_pylint"
            ],
            "stats": dict(tool_stats),
            "features": [
                "langchain_tool_decorators",
                "knowledge_base_integration",
                "multi_dimensional_analysis",
                "mongodb_persistence",
                "shared_resources",
                "thread_safe_operations",
                "pylint_integration"
            ]
        }
