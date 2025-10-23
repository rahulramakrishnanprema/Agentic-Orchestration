# developer_tool.py
"""
Streamlined Developer Tools with @tool decorators
"""
import json
import logging
from datetime import datetime

from typing import Dict, Any, List, Optional
from threading import Lock
from langchain_core.tools import tool
import re
import os
from config.settings import config
from tools.prompt_loader import PromptLoader
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

from config.settings import config as app_config
from services.llm_service import call_llm

logger = logging.getLogger(__name__)

# Shared resources
stats_lock = Lock()
tool_stats = {
    'prompt_generations': 0, 'code_generations': 0, 'code_corrections': 0,
    'total_api_calls': 0, 'errors': 0, 'total_tokens': 0
}

config = None
prompt_loader = None

FILE_EXTENSIONS = {
    "python": ".py", "py": ".py",
    "javascript": ".js", "js": ".js",
    "html": ".html",
    "css": ".css",
    "react": ".jsx",
    "sql": ".sql",
    "yaml": ".yml",

}


def initialize_developer_tools(app_config, app_prompt_loader):
    """Initialize developer tools with config and prompt loader."""
    global config, prompt_loader
    config = app_config
    prompt_loader = app_prompt_loader


def _extract_code_from_llm_response(response_text: str) -> str:
    """Extracts code from a markdown-formatted LLM response."""
    if '```' in response_text:
        match = re.search(r'```(?:\w+\n)?(.*)```', response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return response_text.strip()


def save_files_locally(files: Dict[str, str], issue_key: str):
    """Save generated files to local directory, creating subdirectories as needed."""
    base_folder = "created_project_files"
    project_folder = os.path.join(base_folder, issue_key)
    os.makedirs(project_folder, exist_ok=True)
    for filename, content in files.items():
        path = os.path.join(project_folder, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Saved {filename} to {path}")


@tool
def generate_code_files(deployment_document: Dict[str, Any], issue_key: str,
                        thread_id: str = "unknown", output_queue: Optional[queue.Queue] = None) -> Dict[str, Any]:
    """
    Generate complete connected project code files from deployment document in parallel.
    """
    try:
        with stats_lock:
            tool_stats['code_generations'] += 1
        logging.info(f"[{thread_id}] Generating code files for {issue_key}")

        if not deployment_document:
            logger.error(f"[{thread_id}] Deployment document is empty or None")
            return {"success": False, "error": "Deployment document is empty", "tokens_used": 0}

        generated_files = {}
        total_tokens = 0

        file_structure = deployment_document.get("file_structure", {})
        if not file_structure:
            logger.error(f"[{thread_id}] file_structure is missing from deployment document")
            return {"success": False, "error": "file_structure missing from deployment document", "tokens_used": 0}

        files = file_structure.get("files", [])
        if not files:
            logger.error(f"[{thread_id}] No files defined in file_structure")
            return {"success": False, "error": "No files defined in file_structure", "tokens_used": 0}

        logger.info(f"[{thread_id}] Found {len(files)} files to generate: {[f.get('filename') for f in files]}")

        specs = deployment_document.get("technical_specifications", {})
        implementation_plan = deployment_document.get("implementation_plan", {})
        related_files_summary = deployment_document.get("related_files_summary", "No related files.")

        max_workers = 4

        def generate_single_file(file_info):
            filename = file_info.get('filename', '')
            file_type = file_info.get('type', '')

            if not filename:
                logger.warning(f"[{thread_id}] Skipping file with no filename: {file_info}")
                return None, None, 0

            spec = specs.get(filename, {})
            spec_text = "\n".join([f"{k}: {v}" for k, v in spec.items()])

            prompt = prompt_loader.format(
                "developer_code_generation",
                filename=filename,
                file_type=file_type,
                issue_key=issue_key,
                spec_text=spec_text,
                implementation_plan=json.dumps(implementation_plan, indent=2),
                file_structure=json.dumps(file_structure, indent=2),
                related_files_summary=related_files_summary
            )

            content, tokens = call_llm(prompt, agent_name="developer")
            generated_code = _extract_code_from_llm_response(content)

            if generated_code:
                logging.info(f"[{thread_id}] Generated {filename}: {len(generated_code)} characters")
                save_files_locally({filename: generated_code}, issue_key)
                if output_queue:
                    output_queue.put({"filename": filename, "content": generated_code})
                return filename, generated_code, tokens
            else:
                logger.warning(f"[{thread_id}] Generated code for {filename} is empty")
            return None, None, tokens

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(generate_single_file, file_info) for file_info in files]
            for future in as_completed(futures):
                filename, content, tokens = future.result()
                total_tokens += tokens
                if filename and content:
                    generated_files[filename] = content

        if output_queue:
            output_queue.put(None)

        if not generated_files:
            logger.error(f"[{thread_id}] No files were successfully generated from {len(files)} attempted files")
            return {"success": False, "error": f"No files generated - attempted {len(files)} files",
                    "tokens_used": total_tokens}

        logger.info(
            f"[{thread_id}] Successfully generated {len(generated_files)} files: {list(generated_files.keys())}")
        return {"success": True, "generated_files": generated_files, "tokens_used": total_tokens}
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Code generation exception: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "tokens_used": 0}


@tool
def correct_code_with_feedback(generated_files: Dict[str, str], feedback: List[str],
                               issue_key: str, thread_id: str = "unknown") -> Dict[str, Any]:
    """
    Correct existing code files using feedback from reviewer.
    """
    try:
        with stats_lock:
            tool_stats['code_corrections'] += 1
        logging.info(f"[{thread_id}] Correcting code with feedback for {issue_key}")

        corrected_files = {}
        total_tokens = 0

        # Create a summary of all files for context
        all_files_context = "\n".join([f"--- {fname} ---\n{code}" for fname, code in generated_files.items()])

        for filename, code in generated_files.items():
            formatted_prompt = prompt_loader.format(
                "developer_code_correction",
                issue_key=issue_key,
                filename=filename,
                original_code=code,
                mistakes="\n".join(feedback),
                all_files_context=all_files_context
            )
            content, tokens = call_llm(formatted_prompt, agent_name="developer")
            total_tokens += tokens

            corrected_code = _extract_code_from_llm_response(content)
            corrected_files[filename] = corrected_code
            save_files_locally({filename: corrected_code}, issue_key)

        return {"success": True, "generated_files": corrected_files, "tokens_used": total_tokens}
    except Exception as e:
        with stats_lock:
            tool_stats['errors'] += 1
        logger.error(f"[{thread_id}] Code correction exception: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "tokens_used": 0}


def get_developer_tools_stats() -> Dict[str, Any]:
    with stats_lock:
        return {
            "tool_type": "developer_tools",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "stats": dict(tool_stats),
            "features": [
                "code_generation",
                "code_correction",
                "local_file_saving",
                "statistics_tracking"
            ]
        }
