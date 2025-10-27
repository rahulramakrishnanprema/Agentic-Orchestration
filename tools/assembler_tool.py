# assembler_tool.py
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
from config.settings import config

from json_repair import repair_json
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
    Extract and parse JSON from LLM response, finding the JSON block within the text.
    """
    content = content.strip()
    logger.info(f"[{thread_id}] Response length: {len(content)} chars")

    # Remove markdown code blocks if present
    if content.startswith('```json'):
        content = content[7:-3].strip() if content.endswith('```') else content[7:].strip()
    elif content.startswith('```'):
        content = content[3:-3].strip() if content.endswith('```') else content[3:].strip()

    # Use regex to find the JSON object, making it more robust
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        logger.error(f"[{thread_id}] No JSON object found in response. Preview: {content[:500]}")
        raise ValueError("No JSON object found in LLM response.")

    json_str = json_match.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"[{thread_id}] Initial JSON parse failed: {e}. Attempting repair.")
        try:
            repaired_json_str = repair_json(json_str)
            document = json.loads(repaired_json_str)
            logger.info(f"[{thread_id}] ✓ JSON repaired and parsed successfully.")
            return document
        except Exception as repair_e:
            logger.error(f"[{thread_id}] JSON repair also failed: {repair_e}")
            # Save failed JSON for debugging
            try:
                debug_folder = "debug_json_failures"
                os.makedirs(debug_folder, exist_ok=True)
                debug_file = os.path.join(debug_folder, f"failed_{thread_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.error(f"[{thread_id}] Failed JSON content saved to: {debug_file}")
            except Exception:
                pass
            raise ValueError(f"Invalid JSON from LLM even after repair: {repair_e}")


def _generate_markdown_from_document(document: Dict[str, Any]) -> str:
    """
    Generates a Markdown document from a structured JSON object.
    """
    md_parts = []

    # Metadata and Overview
    metadata = document.get('metadata', {})
    overview = document.get('project_overview', {})
    md_parts.append(f"# {overview.get('title', 'Deployment Document')}")
    md_parts.append(f"**Version:** {metadata.get('version', '1.0')} | **Date:** {metadata.get('generated_at', datetime.now().isoformat())}")
    md_parts.append("\n## Project Overview")
    md_parts.append(overview.get('description', 'No description provided.'))

    # Implementation Plan
    plan = document.get('implementation_plan', {})
    md_parts.append("\n## Implementation Plan")
    md_parts.append(plan.get('strategy', 'No strategy provided.'))
    if plan.get('subtasks'):
        md_parts.append("\n### Subtasks")
        for i, task in enumerate(plan['subtasks']):
            if isinstance(task, dict):
                md_parts.append(f"{i+1}. **{task.get('title', 'Untitled Task')}**: {task.get('description', 'No description.')}")
            else:
                md_parts.append(f"{i+1}. {task}")

    # File Structure
    file_structure = document.get('file_structure', {})
    if file_structure.get('files'):
        md_parts.append("\n## File Structure")
        md_parts.append("```")
        for file_info in file_structure['files']:
            md_parts.append(f"- {file_info.get('path', 'N/A')}: {file_info.get('description', 'No description.')}")
        md_parts.append("```")

    # Technical Specifications
    specs = document.get('technical_specifications', {})
    if specs:
        md_parts.append("\n## Technical Specifications")
        if specs.get('technologies'):
            md_parts.append("- **Technologies:** " + ", ".join(specs['technologies']))
        if specs.get('system_requirements'):
            md_parts.append("- **System Requirements:** " + ", ".join(specs['system_requirements']))

    # Deployment Instructions
    deployment = document.get('deployment_instructions', {})
    if deployment.get('steps'):
        md_parts.append("\n## Deployment Instructions")
        for i, step in enumerate(deployment['steps']):
            md_parts.append(f"{i+1}. {step}")

    return "\n".join(md_parts)


def _validate_document_structure(document: Dict[str, Any], thread_id: str) -> None:
    """
    Validate the deployment document has all required fields with detailed logging.
    Updated to handle missing fields flexibly: core fields get warnings and defaults; optional fields get defaults without errors.
    """
    core_fields = ['metadata', 'project_overview', 'implementation_plan', 'file_structure']
    optional_fields = ['technical_specifications', 'deployment_instructions']

    logger.info(f"[{thread_id}] Validating document structure...")
    logger.info(f"[{thread_id}] Document keys: {list(document.keys())}")

    # Handle missing core fields with warnings and defaults
    for field in core_fields:
        if field not in document:
            logger.warning(f"[{thread_id}] Missing core field '{field}' - using default empty dict")
            document[field] = {}  # Default to empty dict to allow continuation

    # Handle missing optional fields with defaults (no warnings needed)
    for field in optional_fields:
        if field not in document:
            logger.info(f"[{thread_id}] Optional field '{field}' missing - using default empty dict")
            document[field] = {}  # Default to empty dict

    # Validate file_structure sub-fields (critical, but with defaults instead of errors)
    file_structure = document.get('file_structure', {})
    if not file_structure.get('files'):
        logger.warning(f"[{thread_id}] file_structure.files is missing or empty - defaulting to empty list")
        file_structure['files'] = []  # Allow continuation with warning
    if not isinstance(file_structure.get('files'), list):
        logger.warning(f"[{thread_id}] file_structure.files is not a list - defaulting to empty list")
        file_structure['files'] = []

    if not file_structure.get('file_types'):
        logger.warning(f"[{thread_id}] file_structure.file_types is missing - defaulting to empty list")
        file_structure['file_types'] = []

    logger.info(f"[{thread_id}] ✓ Document validated (with defaults applied where needed)")


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

        logger.info(f"[{thread_id}] Calling LLM to generate structured JSON document...")

        content, tokens = call_llm(
            prompt,
            agent_name="assembler",
            max_tokens=config.ASSEMBLER_LLM_MAX_TOKENS,
            temperature=config.ASSEMBLER_LLM_TEMPERATURE,
        )

        logger.info(f"[{thread_id}] LLM returned {tokens} tokens for JSON generation.")

        # Extract and validate JSON
        document = _extract_json_from_response(content, thread_id)
        _validate_document_structure(document, thread_id)

        # Generate Markdown only if LOCAL_STORAGE is enabled
        md_content = ""
        if os.getenv("LOCAL_STORAGE", "True").lower() == "true":
            logger.info(f"[{thread_id}] Generating Markdown documentation from JSON...")
            md_content = _generate_markdown_from_document(document)
            local_folder = "deployment_documents"
            os.makedirs(local_folder, exist_ok=True)
            md_path = os.path.join(local_folder, f"{issue_data.get('key', 'UNKNOWN')}.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"[{thread_id}] ✓ Deployment document saved to {md_path}")
        else:
            logger.info(f"[{thread_id}] Skipping Markdown generation (LOCAL_STORAGE=False)")

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
