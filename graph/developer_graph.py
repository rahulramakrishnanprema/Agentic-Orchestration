import json
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import re
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from tools.developer_tool import correct_code_with_feedback, save_files_locally
from tools.prompt_loader import PromptLoader
from tools.utils import log_activity
from ui.ui import workflow_status, workflow_status_lock
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed  # NEW: Add imports for parallelism
from services.llm_service import call_llm  # Import for per-file generation

logger = logging.getLogger(__name__)

# Initialize prompt loader
prompt_loader = PromptLoader("prompts")


class DeveloperState(TypedDict):
    """State for the developer sub-graph"""
    deployment_document: Dict[str, Any]
    files_to_generate: List[Dict[str, Any]]  # NEW: List of file specs for parallel generation
    thread_id: str
    generated_files: Annotated[Dict[str, str], lambda x, y: {**x, **y}]  # Reducer for merging dicts
    feedback: Optional[List[str]]
    error: str
    global_project_memory: Dict[str, Any]
    related_files: Dict[str, str]
    current_iteration_feedback: List[str]
    issue_data: Dict[str, Any]
    persistent_memory: Dict[str, Any]
    memory_updated: bool
    tokens_used: Annotated[int, lambda x, y: x + y]  # Reducer for summing tokens


def _route_success_or_error(state: DeveloperState) -> str:
    return "error" if state.get("error") else "success"


def _route_feedback(state: DeveloperState) -> str:
    if state.get("feedback"):
        return "correct"
    return "generate"


def _check_feedback_node(state: DeveloperState) -> Dict[str, Any]:
    return state


def _load_memory_context_node(state: DeveloperState) -> Dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    issue_summary = state.get("issue_data", {}).get("summary", "")

    logger.info(f"[DEV-{thread_id}] Loading memory context...")

    # Select related files based on keywords from issue summary
    keywords = issue_summary.lower().split()
    related_files = {}
    for filename, file_data in state['global_project_memory']["all_generated_files"].items():
        if any(kw in filename.lower() for kw in keywords):
            related_files[filename] = file_data["content"]

    state["related_files"] = related_files
    return state


def _plan_files_node(state: DeveloperState) -> Dict[str, Any]:
    """Extract and plan files for parallel generation."""
    file_structure = state['deployment_document'].get('file_structure', {})
    files = file_structure.get('files', [])
    state['files_to_generate'] = files
    return state


def generate_file(state: DeveloperState) -> Dict[str, Any]:
    """Generate code for a single file (called in parallel)."""
    file_info = state['file_info']  # Sub-state for each branch
    filename = file_info.get('filename', '')
    file_type = file_info.get('type', '')

    logger.info(f"[DEV-{state['thread_id']}] Generating {filename}")

    spec = state['deployment_document']['technical_specifications'].get(filename, {})
    spec_text = "\n".join([f"{k}: {v}" for k, v in spec.items()])

    prompt = prompt_loader.format(
        "developer_code_generation",
        filename=filename,
        file_type=file_type,
        issue_key=state['issue_data'].get('key'),
        spec_text=spec_text,
        implementation_plan=json.dumps(state['deployment_document']['implementation_plan'], indent=2),
        file_structure=json.dumps(state['deployment_document']['file_structure'], indent=2)
    )

    content, tokens = call_llm(prompt, agent_name="developer")
    generated_code = content.strip()

    # Clean code block if present
    if '```' in generated_code:
        generated_code = re.sub(r'```.*?\n', '', generated_code, flags=re.DOTALL)
        generated_code = generated_code.rsplit('```', 1)[0].strip()

    return {
        "generated_files": {filename: generated_code},
        "tokens_used": tokens
    }


def _route_to_file_generation(state: DeveloperState) -> List[Send]:
    """Fan-out to parallel file generation nodes."""
    return [Send("generate_file", {"file_info": f, **state}) for f in
            state["files_to_generate"]]  # Pass full state if needed


def _merge_generated_files_node(state: DeveloperState) -> Dict[str, Any]:
    """Fan-in: Merge generated files and proceed to memory update."""
    save_files_locally(state['generated_files'], state['issue_data'].get('key', 'UNKNOWN'))


    return state


def _update_memory_after_generation_node(state: DeveloperState) -> Dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    generated_files = state.get("generated_files", {})
    issue_key = state.get("issue_data", {}).get("key", "UNKNOWN")

    logger.info(f"[DEV-{thread_id}] Updating memory after generation...")

    # Assume global_project_memory is passed in state
    global_project_memory = state['global_project_memory']

    # Update all_generated_files
    for filename, content in generated_files.items():
        global_project_memory["all_generated_files"][filename] = {
            "metadata": {},
            "content": content
        }

    # Extract and update file_relationships
    for filename, content in generated_files.items():
        imports = re.findall(r'from\s+(\w+)\s+import|import\s+(\w+)', content)
        refs = [imp for sublist in imports for imp in sublist if imp]
        global_project_memory["file_relationships"][filename] = refs

    # Append to issue_history
    global_project_memory["issue_history"].append(issue_key)

    state["persistent_memory"] = global_project_memory
    state["memory_updated"] = True

    # MongoDB storage is now handled by JiraDeveloperWorkflow - removed duplicate call

    return state


def _accumulate_feedback_node(state: DeveloperState) -> Dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    current_iteration_feedback = state.get("feedback", [])  # NEW: Use feedback from state

    logger.info(f"[DEV-{thread_id}] Accumulating feedback...")

    state["current_iteration_feedback"] = current_iteration_feedback

    # Add new unique mistakes to cumulative
    global_project_memory = state['global_project_memory']
    for mistake in current_iteration_feedback:
        if mistake not in global_project_memory["cumulative_mistakes"]:
            global_project_memory["cumulative_mistakes"].append(mistake)

    return state


def _correct_code_node(state: DeveloperState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "DeveloperAgent"
    thread_id = state.get("thread_id", "unknown")
    generated_files = state.get("generated_files", {})
    feedback = state.get("feedback", [])  # NEW: Use feedback from state
    file_types = state.get("file_types", [])
    issue_data = state.get("issue_data", {})

    logger.info(f"[DEV-{thread_id}] Correcting code with feedback...")

    try:
        result = correct_code_with_feedback.invoke({
            "generated_files": generated_files,
            "feedback": feedback,
            "file_types": file_types,
            "issue_key": issue_data.get('key', 'UNKNOWN'),
            "thread_id": thread_id
        })

        if result.get("success"):
            corrected_files = result.get("generated_files", {})
            save_files_locally(corrected_files, issue_data.get('key', 'UNKNOWN'))
            logger.info(f"[DEV-{thread_id}] Saved {len(corrected_files)} corrected files locally")
            state["tokens_used"] += result.get("tokens_used", 0)
            return {"generated_files": corrected_files}
        else:
            return {"error": result.get("error", "Code correction failed")}
    except Exception as error:
        logger.error(f"[DEV-{thread_id}] Code correction failed: {error}")
        return {"error": str(error)}


def _update_memory_after_correction_node(state: DeveloperState) -> Dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    current_iteration_feedback = state.get("current_iteration_feedback", [])

    logger.info(f"[DEV-{thread_id}] Updating memory after correction...")

    global_project_memory = state['global_project_memory']
    global_project_memory["resolved_mistakes"].extend(current_iteration_feedback)

    state["persistent_memory"] = global_project_memory
    state["memory_updated"] = True

    # MongoDB storage is now handled by JiraDeveloperWorkflow - removed duplicate call

    return state


def _compile_results_node(state: DeveloperState) -> Dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    generated_files = state.get("generated_files", {})
    issue_data = state.get("issue_data", {})

    logger.info(f"[DEV-{thread_id}] Compiling results...")

    return {
        "final_result": {
            "success": True,
            "generated_files": generated_files,
            "files_created": list(generated_files.keys()),
            "issue_key": issue_data.get('key', 'UNKNOWN'),
            "workflow_type": "simplified_langgraph_developer"
        }
    }


def _handle_error_node(state: DeveloperState) -> Dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    error_msg = state.get("error", "Unknown error")

    logger.error(f"[DEV-{thread_id}] Workflow error: {error_msg}")

    return {
        "final_result": {
            "success": False,
            "error": error_msg,
            "workflow_type": "simplified_langgraph_developer"
        }
    }


def build_developer_graph():
    graph = StateGraph(DeveloperState)
    # Add nodes
    graph.add_node("check_feedback", _check_feedback_node)
    graph.add_node("load_memory_context", _load_memory_context_node)
    graph.add_node("plan_files", _plan_files_node)
    graph.add_node("generate_file", generate_file)  # Parallel target
    graph.add_node("merge_generated_files", _merge_generated_files_node)
    graph.add_node("update_memory_after_generation", _update_memory_after_generation_node)
    graph.add_node("accumulate_feedback", _accumulate_feedback_node)
    graph.add_node("correct_code", _correct_code_node)
    graph.add_node("update_memory_after_correction", _update_memory_after_correction_node)
    graph.add_node("compile_results", _compile_results_node)
    graph.add_node("handle_error", _handle_error_node)
    # Edges
    graph.add_edge(START, "check_feedback")
    graph.add_conditional_edges("check_feedback", _route_feedback,
                                {"generate": "load_memory_context", "correct": "accumulate_feedback"})
    graph.add_edge("load_memory_context", "plan_files")
    graph.add_conditional_edges("plan_files", _route_to_file_generation, ["generate_file"])
    graph.add_edge("generate_file", "merge_generated_files")
    graph.add_edge("merge_generated_files", "update_memory_after_generation")
    graph.add_conditional_edges("update_memory_after_generation", _route_success_or_error,
                                {"success": "compile_results", "error": "handle_error"})
    graph.add_conditional_edges("accumulate_feedback", _route_success_or_error,
                                {"success": "correct_code", "error": "handle_error"})
    graph.add_conditional_edges("correct_code", _route_success_or_error,
                                {"success": "update_memory_after_correction", "error": "handle_error"})
    graph.add_conditional_edges("update_memory_after_correction", _route_success_or_error,
                                {"success": "compile_results", "error": "handle_error"})
    graph.add_edge("compile_results", END)
    graph.add_edge("handle_error", END)
    return graph.compile()