# C:\Users\Rahul\Agent-flow\tools\assembler_tool.py
"""
Assembler Tools - Creates deployment documents from subtasks
"""
import json
import logging
from typing import Dict, Any, List
from langchain_core.tools import tool
from datetime import datetime
import os
import re

from services.llm_service import call_llm

logger = logging.getLogger(__name__)

# Shared configuration (initialized by main system)
config = None
prompt_loader = None


def initialize_assembler_tools(app_config, app_prompt_loader):
    global config, prompt_loader
    config = app_config
    prompt_loader = app_prompt_loader


def _extract_json_from_response(content: str, thread_id: str) -> Dict[str, Any]:
    """
    Robustly extract and parse JSON from LLM response with comprehensive error handling
    """
    original_content = content
    content = content.strip()

    # Log the response for debugging
    logger.info(f"[{thread_id}] Response length: {len(content)} chars")
    logger.info(f"[{thread_id}] Response starts with: {content[:100]}")
    logger.info(f"[{thread_id}] Response ends with: ...{content[-100:]}")

    # Remove markdown code blocks if present
    if content.startswith('```json'):
        content = content[7:]
        logger.info(f"[{thread_id}] Removed ```json prefix")
    elif content.startswith('```'):
        content = content[3:]
        logger.info(f"[{thread_id}] Removed ``` prefix")

    if content.endswith('```'):
        content = content[:-3]
        logger.info(f"[{thread_id}] Removed ``` suffix")

    content = content.strip()

    # Check if response looks like markdown instead of JSON
    if content.startswith('#') or content.startswith('##'):
        logger.error(f"[{thread_id}] LLM returned Markdown instead of JSON")
        logger.error(f"[{thread_id}] First 500 chars: {content[:500]}")
        raise ValueError("LLM returned Markdown format instead of JSON. The prompt instructions were not followed.")

    # Try direct JSON parse first (most common case)
    if content.startswith('{'):
        try:
            document = json.loads(content)
            logger.info(f"[{thread_id}] Successfully parsed JSON directly")
            return document
        except json.JSONDecodeError as e:
            logger.warning(f"[{thread_id}] Direct JSON parse failed: {e}")

    # Use brace-counting to extract complete JSON object
    first_brace = content.find('{')
    if first_brace == -1:
        logger.error(f"[{thread_id}] No opening brace found in response")
        logger.error(f"[{thread_id}] Full response: {original_content[:1000]}")
        raise ValueError("No JSON object found in LLM response")

    # Count braces to find the matching closing brace
    brace_depth = 0
    in_string = False
    escape_next = False
    end_pos = -1

    for i in range(first_brace, len(content)):
        char = content[i]

        # Handle string escaping
        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        # Handle strings (ignore braces inside strings)
        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
                if brace_depth == 0:
                    end_pos = i + 1
                    break

    if end_pos == -1:
        logger.error(f"[{thread_id}] Could not find matching closing brace")
        logger.error(f"[{thread_id}] Brace depth at end: {brace_depth}")
        raise ValueError("JSON is truncated - no matching closing brace found. Try increasing max_tokens.")

    json_str = content[first_brace:end_pos]
    logger.info(f"[{thread_id}] Extracted JSON of length {len(json_str)} characters")

    try:
        document = json.loads(json_str)
        logger.info(f"[{thread_id}] Successfully parsed extracted JSON")
        return document
    except json.JSONDecodeError as e:
        logger.error(f"[{thread_id}] JSON parse error: {e}")
        logger.error(f"[{thread_id}] Error at position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
        logger.error(f"[{thread_id}] JSON starts with: {json_str[:500]}")
        logger.error(f"[{thread_id}] JSON ends with: ...{json_str[-500:]}")
        raise ValueError(f"Failed to parse JSON: {e}")


def _validate_document_structure(document: Dict[str, Any], thread_id: str) -> None:
    """
    Validate the deployment document has all required fields with detailed logging
    """
    required_fields = [
        'metadata', 'project_overview', 'implementation_plan',
        'file_structure', 'technical_specifications', 'deployment_instructions'
    ]

    logger.info(f"[{thread_id}] Validating document structure...")
    logger.info(f"[{thread_id}] Document keys: {list(document.keys())}")

    missing_fields = [field for field in required_fields if field not in document]

    if missing_fields:
        logger.error(f"[{thread_id}] Missing required fields: {', '.join(missing_fields)}")
        logger.error(f"[{thread_id}] Available fields: {', '.join(document.keys())}")
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate file_structure
    file_structure = document.get('file_structure', {})
    if not file_structure.get('files'):
        raise ValueError("file_structure.files is required and cannot be empty")

    if not isinstance(file_structure.get('files'), list):
        raise ValueError("file_structure.files must be a list")

    if not file_structure.get('file_types'):
        raise ValueError("file_structure.file_types is required")

    logger.info(f"[{thread_id}] ✓ Document validated: {len(file_structure.get('files', []))} files")


@tool
def generate_deployment_document(
        issue_data: Dict[str, Any],
        subtasks: List[Dict[str, Any]],
        thread_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Generate comprehensive deployment document in one LLM call, store MD locally.
    """
    try:
        logger.info(f"[{thread_id}] Generating full deployment document...")

        summary = issue_data.get('summary', '')
        description = issue_data.get('description', '')

        subtasks_text = "\n".join([
            f"- Subtask {i + 1}: {st.get('description', '')}"
            for i, st in enumerate(subtasks)
        ])

        # Generate JSON document with high max_tokens
        prompt = prompt_loader.format(
            "assembler_full_deployment",
            summary=summary,
            description=description,
            subtasks_text=subtasks_text
        )

        logger.info(f"[{thread_id}] Calling LLM with max_tokens=32000...")

        content, tokens = call_llm(
            prompt,
            agent_name="assembler",
            max_tokens=32000,
            temperature=0.2
        )

        logger.info(f"[{thread_id}] LLM returned {tokens} tokens")

        # Extract and validate JSON
        document = _extract_json_from_response(content, thread_id)
        _validate_document_structure(document, thread_id)

        # Generate Markdown from validated JSON
        logger.info(f"[{thread_id}] Generating Markdown documentation...")
        json_document = json.dumps(document, indent=2)
        md_prompt = prompt_loader.format(
            "assembler_md_render",
            json_document=json_document
        )

        md_content, md_tokens = call_llm(
            md_prompt,
            agent_name="assembler",
            max_tokens=4000
        )
        tokens += md_tokens

        # Clean MD content
        md_content = md_content.strip()
        if md_content.startswith('```markdown'):
            md_content = md_content[11:]
        elif md_content.startswith('```'):
            md_content = md_content[3:]
        if md_content.endswith('```'):
            md_content = md_content[:-3]
        md_content = md_content.strip()

        # Store MD locally
        local_folder = "deployment_documents"
        os.makedirs(local_folder, exist_ok=True)
        md_path = os.path.join(local_folder, f"{issue_data.get('key', 'UNKNOWN')}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        logger.info(f"[{thread_id}] ✓ Deployment document saved to {md_path}")

        return {
            "success": True,
            "document": document,
            "markdown": md_content,
            "tokens_used": tokens
        }

    except ValueError as ve:
        # Specific validation errors
        logger.error(f"[{thread_id}] Validation error: {str(ve)}")
        return {"success": False, "error": f"Validation error: {str(ve)}", "tokens_used": 0}
    except Exception as e:
        # General errors
        logger.error(f"[{thread_id}] Document generation failed: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "tokens_used": 0}