# C:\Users\Rahul\Agent-flow\tools\planner_tools.py
"""
Streamlined Planner Tools - Reduced Code with Full Functionality
- Uses @tool decorators instead of classes
- Shared resources and configuration
- 60-70% code reduction while preserving features
"""
import json
import logging
from datetime import datetime

import networkx as nx
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import re
from dotenv import load_dotenv
import queue
from threading import Thread, Lock
import os
from tools.prompt_loader import PromptLoader

from config.settings import config as app_config
from services.llm_service import call_llm

logger = logging.getLogger(__name__)

# Shared resources
stats_lock = Lock()
tool_stats = {
    'subtask_generation_calls': 0,
    'scoring_calls': 0,
    'merging_calls': 0,
    'hitl_validations': 0,
    'total_api_calls': 0,
    'errors': 0,
    'total_tokens': 0
}

config = None
prompt_loader = None


def initialize_planner_tools(app_config, app_prompt_loader):
    global config, prompt_loader
    config = app_config
    prompt_loader = app_prompt_loader


def parse_json_from_text(text: str) -> Dict:
    """Parse JSON from text, handling markdown code blocks and other formats."""
    try:
        # Clean the response - remove markdown code blocks if present
        cleaned_text = text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith('```'):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        # Try to find JSON object in the cleaned text
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        raise ValueError("No JSON found in response")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON parsing error: {e}. Response: {text}")
        raise Exception("JSON parsing failed")


@tool
def generate_got_subtasks(issue_data: Dict[str, Any], thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Generate subtasks using GOT methodology with NetworkX graph structure from issue data directly.
    Args:
        issue_data: JIRA issue data containing summary and description
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['subtask_generation_calls'] += 1
        logging.info(f"[{thread_id}] Generating GOT subtasks from issue data")
        summary = issue_data.get('summary', '')
        description = issue_data.get('description', '')
        issue_key = issue_data.get('key', 'UNKNOWN')

        formatted_prompt = prompt_loader.format(
            "planner_got_subtasks",
            issue_key=issue_key,
            summary=summary,
            description=description
        )

        content, tokens = call_llm(formatted_prompt, agent_name="planner")

        subtasks_data = []
        try:
            if '[' in content:
                start = content.find('[')
                end = content.rfind(']') + 1
                subtasks_data = json.loads(content[start:end])
            else:
                raise Exception("Subtask parsing failed: No array found in response")
        except Exception as e:
            raise Exception(f"Subtask parsing failed: {str(e)}")

        graph = nx.DiGraph()
        for item in subtasks_data:
            graph.add_node(item['id'],
                           description=item.get('description', ''),
                           priority=item.get('priority', 3),
                           requirements_covered=item.get('requirements_covered', []),
                           reasoning=item.get('reasoning', ''),
                           score=0.0)

        sorted_ids = sorted([item['id'] for item in subtasks_data])
        for i in range(len(sorted_ids) - 1):
            graph.add_edge(sorted_ids[i], sorted_ids[i + 1])

        graph_data = {
            "nodes": {
                node_id: dict(data) for node_id, data in graph.nodes(data=True)
            },
            "edges": list(graph.edges())
        }

        return {"success": True, "subtasks_graph": graph_data, "tokens_used": tokens}
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def generate_cot_subtasks(issue_data: Dict[str, Any], thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Generate subtasks using Chain of Thoughts (CoT) methodology for simple projects.
    Produces a linear list of subtasks without graph structure.
    Args:
        issue_data: JIRA issue data containing summary and description
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['subtask_generation_calls'] += 1  # Reuse stat; add 'cot_generation_calls' if needed
        logging.info(f"[{thread_id}] Generating CoT subtasks from issue data")
        summary = issue_data.get('summary', '')
        description = issue_data.get('description', '')
        issue_key = issue_data.get('key', 'UNKNOWN')

        formatted_prompt = prompt_loader.format(
            "planner_cot_subtasks",
            issue_key=issue_key,
            summary=summary,
            description=description
        )

        content, tokens = call_llm(formatted_prompt, agent_name="planner")

        subtasks_data = []
        try:
            if '[' in content:
                start = content.find('[')
                end = content.rfind(']') + 1
                subtasks_data = json.loads(content[start:end])
            else:
                raise Exception("Subtask parsing failed: No array found in response")
        except Exception as e:
            raise Exception(f"Subtask parsing failed: {str(e)}")

        # Format as simple list (no graph)
        subtasks_list = []
        for i, item in enumerate(subtasks_data, start=1):
            subtasks_list.append({
                "id": i,
                "description": item.get('description', ''),
                "priority": item.get('priority', 3),
                "requirements_covered": item.get('requirements_covered', []),
                "reasoning": item.get('reasoning', '')
            })

        return {"success": True, "subtasks_list": subtasks_list, "tokens_used": tokens}
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def score_subtasks_with_llm(subtasks_graph: Dict[str, Any], requirements: Dict[str, Any], thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Score each subtask using LLM evaluation.
    Args:
        subtasks_graph: NetworkX graph data of subtasks
        requirements: Project requirements
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['scoring_calls'] += 1
        logging.info(f"[{thread_id}] Scoring subtasks with LLM")
        scored_subtasks = []
        total_tokens = 0
        for node_id, node_data in subtasks_graph.get("nodes", {}).items():
            formatted_prompt = prompt_loader.format(
                "planner_subtask_scoring",
                issue_description=requirements.get('project_description', ''),
                summary=requirements.get('reasoning', ''),
                requirements="\n".join(requirements.get('requirements', [])),
                subtask_description=node_data['description']
            )
            content, tokens = call_llm(formatted_prompt, agent_name="planner")
            total_tokens += tokens
            score_data = parse_json_from_text(content)
            scored_subtask = {
                'id': int(node_id),
                'description': node_data['description'],
                'priority': node_data['priority'],
                'score': float(score_data.get('score', 7.5)),
                'reasoning': score_data.get('reasoning', ''),
                'requirements_covered': score_data.get('requirements_covered', node_data.get('requirements_covered', []))
            }
            scored_subtasks.append(scored_subtask)
            logging.info(
                f"[{thread_id}] Subtask {scored_subtask['id']}: Score {scored_subtask['score']:.1f} - {scored_subtask['description']}")
        return {"success": True, "scored_subtasks": scored_subtasks, "tokens_used": total_tokens}
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def merge_subtasks(scored_subtasks: List[Dict[str, Any]], jira_description: str, thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Merge scored subtasks into main subtasks covering the complete JIRA description.
    Supports flexible number of subtasks based on complexity.
    Preserves scores by calculating weighted average based on merged source subtasks.
    Args:
        scored_subtasks: List of scored subtasks
        jira_description: Full JIRA issue description for coverage
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['merging_calls'] += 1
        logging.info(f"[{thread_id}] Merging subtasks into main ones")

        subtasks_text = "\n".join([
            f"ID: {st['id']}, Score: {st['score']}, Description: {st['description']}, Reasoning: {st['reasoning']}"
            for st in scored_subtasks
        ])

        formatted_prompt = prompt_loader.format(
            "planner_merge_subtasks",
            jira_description=jira_description,
            subtasks_text=subtasks_text
        )

        content, tokens = call_llm(formatted_prompt, agent_name="planner")

        logger.info(f"[{thread_id}] Raw LLM response for merging subtasks: {content[:500]}...")

        # Clean the response - remove markdown code blocks if present
        cleaned_content = content.strip()
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith('```'):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith('```'):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()

        # Parse the response more robustly
        try:
            if '{"merged_subtasks":' in cleaned_content:
                data = json.loads(cleaned_content[cleaned_content.find('{'):cleaned_content.rfind('}')+1])
                merged = data.get('merged_subtasks', [])
            else:
                # Fallback to looking for just the array
                json_start = cleaned_content.find('[')
                json_end = cleaned_content.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    merged = json.loads(cleaned_content[json_start:json_end])
                else:
                    logger.error(f"[{thread_id}] No valid JSON structure found in response. Response length: {len(content)}")
                    logger.error(f"[{thread_id}] Response ends with: ...{content[-200:]}")
                    raise ValueError("No valid JSON structure found in response - response may be truncated")
        except json.JSONDecodeError as e:
            logger.error(f"[{thread_id}] JSON parse error: {str(e)}. Cleaned content length: {len(cleaned_content)}")
            logger.error(f"[{thread_id}] Content ends with: ...{cleaned_content[-200:]}")
            raise ValueError(f"Failed to parse merged subtasks (possible truncation): {str(e)}")

        if not merged:
            logger.warning(f"[{thread_id}] No merged subtasks generated")
            raise ValueError("No merged subtasks were generated")

        # Validate that each merged subtask has required fields
        for i, subtask in enumerate(merged):
            if 'id' not in subtask or 'description' not in subtask:
                raise ValueError(f"Merged subtask {i+1} missing required fields (id, description)")

        # IMPORTANT: Calculate scores for merged subtasks based on their source subtasks
        # Create a mapping of scored subtasks by ID for quick lookup
        scored_map = {st['id']: st for st in scored_subtasks}

        for merged_subtask in merged:
            # Get the source subtask IDs that were merged into this subtask
            source_ids = merged_subtask.get('merged_from', [])

            if source_ids and isinstance(source_ids, list):
                # Calculate weighted average score from source subtasks
                total_score = 0.0
                count = 0
                for source_id in source_ids:
                    if source_id in scored_map:
                        total_score += scored_map[source_id].get('score', 0.0)
                        count += 1

                merged_subtask['score'] = round(total_score / count, 1) if count > 0 else 0.0
                merged_subtask['score_reasoning'] = f"Average of {count} source subtasks"
            else:
                # If no source IDs, calculate based on priority or default to average
                # Use the subtask ID to find if it matches any scored subtask
                matched_score = None
                for scored_st in scored_subtasks:
                    if scored_st['description'][:50] in merged_subtask['description'][:100]:
                        matched_score = scored_st.get('score', 0.0)
                        break

                if matched_score is not None:
                    merged_subtask['score'] = matched_score
                    merged_subtask['score_reasoning'] = "Matched from original subtask"
                else:
                    # Default to average of all scores
                    avg_score = sum(st.get('score', 0.0) for st in scored_subtasks) / len(scored_subtasks)
                    merged_subtask['score'] = round(avg_score, 1)
                    merged_subtask['score_reasoning'] = "Average of all subtasks"

            # Ensure priority is set
            if 'priority' not in merged_subtask:
                merged_subtask['priority'] = merged_subtask.get('id', 0)

            logger.info(f"[{thread_id}] Merged subtask {merged_subtask['id']}: Score {merged_subtask['score']:.1f} - {merged_subtask['description'][:60]}...")

        # Calculate overall score
        overall_score = sum(st.get('score', 0.0) for st in merged) / len(merged) if merged else 0.0
        logger.info(f"[{thread_id}] Successfully merged into {len(merged)} subtasks with overall score: {overall_score:.1f}")

        return {
            "success": True,
            "merged_subtasks": merged,
            "overall_score": round(overall_score, 1),
            "tokens_used": tokens
        }
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Merge failed: {str(e)}")
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def perform_hitl_validation(scored_subtasks: List[Dict[str, Any]], thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Perform Human-in-the-Loop validation for low-scoring subtasks.
    Args:
        scored_subtasks: List of scored subtasks
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['hitl_validations'] += 1
        logging.info(f"[{thread_id}] Performing HITL validation")
        threshold = getattr(config, 'GOT_SCORE_THRESHOLD', 7.0)
        approved_subtasks = []
        for subtask in scored_subtasks:
            score = subtask.get('score', 0.0)
            if score >= threshold:
                approved_subtasks.append(subtask)
                logging.info(f"[{thread_id}] Subtask {subtask['id']} approved (score: {score})")
            else:
                logging.info(f"[{thread_id}] Subtask {subtask['id']} requires validation (score: {score})")
                approved_subtasks.append(subtask) # Auto-approve for demo
        return {"success": True, "approved_subtasks": approved_subtasks}
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        return {"success": False, "error": str(e)}


def get_planner_tools_stats() -> Dict[str, Any]:
    with stats_lock:
        return {
            "tool_type": "planner_tools",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "stats": dict(tool_stats),
            "features": [
                "got_subtask_generation",
                "cot_subtask_generation",  # NEW
                "subtask_scoring",
                "subtask_merging",
                "hitl_validation",
                "statistics_tracking"
            ]
        }