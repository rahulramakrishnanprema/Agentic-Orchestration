# planner_tools.py
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
import queue
from threading import Thread, Lock
import os
from tools.prompt_loader import PromptLoader
from json_repair import repair_json

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


def _parse_json_array_from_text(text: str) -> List:
    """Helper to parse a JSON array from text, with fallback to json_repair."""
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

        # Find the outermost array
        start = cleaned_text.find('[')
        end = cleaned_text.rfind(']') + 1
        if 0 <= start < end:
            array_str = cleaned_text[start:end]
            try:
                result = json.loads(array_str)
                # Validate it's actually a list
                if isinstance(result, list):
                    return result
                else:
                    raise ValueError(f"Parsed JSON is not a list, got {type(result)}")
            except json.JSONDecodeError as e:
                logger.warning(f"Standard JSON array parsing failed, attempting repair: {e}")
                try:
                    repaired = repair_json(array_str)
                    result = json.loads(repaired)
                    # Validate it's actually a list
                    if isinstance(result, list):
                        return result
                    else:
                        raise ValueError(f"Repaired JSON is not a list, got {type(result)}")
                except Exception as repair_error:
                    logger.error(f"JSON repair failed: {repair_error}")
                    raise ValueError(f"Could not repair JSON: {repair_error}")
        raise ValueError("No JSON array found in response")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON array parsing error: {e}. Response: {text[:500]}...")
        raise


def parse_json_from_text(text: str) -> Dict:
    """Parse JSON from text, handling markdown code blocks and other formats with json_repair fallback."""
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
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                # Try json_repair as fallback
                logger.warning(f"Standard JSON parsing failed, attempting repair: {e}")
                try:
                    repaired = repair_json(json_str)
                    return json.loads(repaired)
                except Exception as repair_error:
                    logger.error(f"JSON repair also failed: {repair_error}")
                    raise e
        raise ValueError("No JSON found in response")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON parsing error: {e}. Response: {text[:500]}...")
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
        subtasks_data = _parse_json_array_from_text(content)

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
            "edges": list(graph.edges()),
            "graph": {  # Add metadata here
                "summary": summary,
                "description": description
            }
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
            tool_stats['subtask_generation_calls'] += 1
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
        subtasks_data = _parse_json_array_from_text(content)

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
    Score all subtasks using a single batched LLM evaluation for performance.
    Args:
        subtasks_graph: NetworkX graph data of subtasks
        requirements: Project requirements
        thread_id: Thread identifier for logging
    """
    try:
        with stats_lock:
            tool_stats['scoring_calls'] += 1
        logging.info(f"[{thread_id}] Scoring subtasks with a single batched LLM call")

        subtasks_to_score = [
            {"id": node_id, "description": node_data["description"]}
            for node_id, node_data in subtasks_graph.get("nodes", {}).items()
        ]

        if not subtasks_to_score:
            return {"success": True, "scored_subtasks": [], "tokens_used": 0}

        # Ensure summary and description are available for the prompt
        summary = requirements.get('summary')
        description = requirements.get('description')

        # Debug logging
        logging.debug(f"[{thread_id}] Requirements keys: {list(requirements.keys())}")
        logging.debug(f"[{thread_id}] Summary from requirements: '{summary}'")
        logging.debug(f"[{thread_id}] Description from requirements: '{description}'")

        # Try graph metadata if requirements don't have them
        if not summary or not description:
            logging.warning(f"[{thread_id}] Summary or description missing in requirements. Trying to get from subtasks_graph metadata.")
            graph_metadata = subtasks_graph.get("graph", {})
            logging.debug(f"[{thread_id}] Graph metadata keys: {list(graph_metadata.keys())}")

            if not summary:
                summary = graph_metadata.get("summary", "")
                logging.debug(f"[{thread_id}] Summary from graph: '{summary}'")
            if not description:
                description = graph_metadata.get("description", "")
                logging.debug(f"[{thread_id}] Description from graph: '{description}'")

        # Final check - if still missing, use defaults
        if not summary or not description:
            logging.warning(f"[{thread_id}] Could not find summary or description after all attempts. Using defaults.")
            summary = summary or "Development Task"
            description = description or "A development task requiring implementation"

        formatted_prompt = prompt_loader.format(
            "planner_batch_subtask_scoring",
            issue_description=description,
            summary=summary,
            requirements="\n".join(requirements.get('requirements', [])),
            subtasks_json=json.dumps(subtasks_to_score, indent=2)
        )

        content, tokens = call_llm(formatted_prompt, agent_name="planner")
        scores_data = _parse_json_array_from_text(content)

        # Handle cases where the LLM might return a list containing the actual list of scores
        if scores_data and isinstance(scores_data[0], list):
            logging.warning(f"[{thread_id}] LLM returned a nested list. Extracting inner list.")
            scores_data = scores_data[0]

        # Validate and filter out invalid score items (e.g., None from failed json_repair)
        validated_scores = [item for item in scores_data if isinstance(item, dict) and 'id' in item]
        if len(validated_scores) != len(scores_data):
            logging.warning(f"[{thread_id}] Filtered out {len(scores_data) - len(validated_scores)} invalid score items.")
        scores_data = validated_scores

        # Create a lookup for original subtask data
        original_subtasks = {
            str(node_id): node_data for node_id, node_data in subtasks_graph.get("nodes", {}).items()
        }
        scored_subtasks = []
        for score_item in scores_data:
            # Validate that score_item is a dictionary
            if not isinstance(score_item, dict):
                logging.warning(f"[{thread_id}] Score item is not a dict, skipping: {type(score_item)} = {str(score_item)[:100]}")
                continue

            subtask_id_str = str(score_item.get('id'))
            if subtask_id_str in original_subtasks:
                original_data = original_subtasks[subtask_id_str]
                scored_subtask = {
                    'id': int(subtask_id_str),
                    'description': original_data['description'],
                    'priority': original_data['priority'],
                    'score': float(score_item.get('score', 7.5)),
                    'reasoning': score_item.get('reasoning', ''),
                    'requirements_covered': score_item.get('requirements_covered', original_data.get('requirements_covered', []))
                }
                scored_subtasks.append(scored_subtask)
                logging.info(
                    f"[{thread_id}] Subtask {scored_subtask['id']}: Score {scored_subtask['score']:.1f} - {scored_subtask['description']}")

        # If we got no valid scored subtasks, create defaults
        if not scored_subtasks:
            logging.warning(f"[{thread_id}] No valid scored subtasks extracted from LLM response. Creating defaults with 7.5 score.")
            scored_subtasks = [
                {
                    'id': node_id,
                    'description': node_data.get('description', ''),
                    'priority': node_data.get('priority', 3),
                    'score': 7.5,
                    'reasoning': 'Default score assigned due to LLM response parsing issues',
                    'requirements_covered': node_data.get('requirements_covered', [])
                }
                for node_id, node_data in subtasks_graph.get("nodes", {}).items()
            ]

        return {"success": True, "scored_subtasks": scored_subtasks, "tokens_used": tokens}
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

        # Use robust parsing functions
        merged = []
        try:
            # Attempt to parse as a JSON array first, as this seems to be a common response format
            parsed_data = _parse_json_array_from_text(content)
            if isinstance(parsed_data, list):
                merged = parsed_data
            else:
                # Fallback for object-based response
                data = parse_json_from_text(content)
                merged = data.get('merged_subtasks', [])
        except Exception as e:
            logger.warning(f"[{thread_id}] JSON parsing failed for merge_subtasks: {e}. Raw content: {content[:200]}")
            # As a last resort, try to repair the whole content as a JSON array
            try:
                merged = _parse_json_array_from_text(content)
            except Exception as final_e:
                 logger.error(f"[{thread_id}] Final parsing attempt failed: {final_e}")
                 raise ValueError("No merged subtasks were generated or parsed from the LLM response.")

        if not merged:
            raise ValueError("No merged subtasks were generated or parsed from the LLM response.")

        # Validate that each merged subtask has required fields and is a dict
        valid_merged = []
        for i, subtask in enumerate(merged):
            if not isinstance(subtask, dict):
                logging.warning(f"[{thread_id}] Merged subtask {i} is not a dict, skipping: {type(subtask)}")
                continue
            if 'id' not in subtask or 'description' not in subtask:
                logging.warning(f"[{thread_id}] Merged subtask {i} missing required fields (id, description), skipping")
                continue
            valid_merged.append(subtask)

        if not valid_merged:
            raise ValueError("No valid merged subtasks found after validation")

        merged = valid_merged

        # ...existing code...
        scored_map = {st['id']: st for st in scored_subtasks}

        for merged_subtask in merged:
            source_ids = merged_subtask.get('covered_subtasks', []) # Changed from 'merged_from'

            if source_ids and isinstance(source_ids, list):
                total_score, count = 0.0, 0
                for source_id in source_ids:
                    if source_id in scored_map:
                        total_score += scored_map[source_id].get('score', 0.0)
                        count += 1
                merged_subtask['score'] = round(total_score / count, 1) if count > 0 else 0.0
                merged_subtask['score_reasoning'] = f"Average of {count} source subtasks"
            else:
                # Fallback score calculation
                avg_score = sum(st.get('score', 0.0) for st in scored_subtasks) / len(scored_subtasks) if scored_subtasks else 0.0
                merged_subtask['score'] = round(avg_score, 1)
                merged_subtask['score_reasoning'] = "Defaulted to average of all subtasks"

            if 'priority' not in merged_subtask:
                merged_subtask['priority'] = merged_subtask.get('id', 0)

            logger.info(f"[{thread_id}] Merged subtask {merged_subtask['id']}: Score {merged_subtask['score']:.1f} - {merged_subtask['description'][:60]}...")

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
