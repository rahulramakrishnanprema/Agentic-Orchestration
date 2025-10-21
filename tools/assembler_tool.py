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
    Extract and parse JSON from LLM response - relies on prompt enforcement for valid JSON
    """
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

    # Try direct JSON parse
    if content.startswith('{'):
        try:
            document = json.loads(content)
            logger.info(f"[{thread_id}] ✓ Successfully parsed JSON directly")
            return document
        except json.JSONDecodeError as e:
            logger.warning(f"[{thread_id}] Initial JSON parse failed: {e} - Attempting repair")
            # Repair the JSON using json_repair
            repaired_content = repair_json(content, skip_json_loads=True)  # Fast mode for known invalids
            try:
                document = json.loads(repaired_content)
                logger.info(f"[{thread_id}] ✓ JSON repaired and parsed successfully")
                return document
            except json.JSONDecodeError as repair_e:
                logger.error(f"[{thread_id}] JSON repair failed: {repair_e}")
                # Save failed JSON for debugging
                try:
                    debug_folder = "debug_json_failures"
                    os.makedirs(debug_folder, exist_ok=True)
                    debug_file = os.path.join(debug_folder, f"failed_{thread_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.error(f"[{thread_id}] Failed JSON saved to: {debug_file}")
                except:
                    pass
                raise ValueError(f"Invalid JSON from LLM after repair: {repair_e}. The response must be valid JSON. Check that all braces and brackets are closed properly.")

    # No opening brace found
    logger.error(f"[{thread_id}] No JSON object found in response")
    logger.error(f"[{thread_id}] Full response preview: {content[:500]}")
    raise ValueError("No JSON object found in LLM response. Response must start with {")


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

        logger.info(f"[{thread_id}] Calling LLM ...")

        content, tokens = call_llm(
            prompt,
            agent_name="assembler",
            max_tokens=config.ASSEMBLER_LLM_MAX_TOKENS,
            temperature=config.ASSEMBLER_LLM_TEMPERATURE,
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
            max_tokens=config.ASSEMBLER_LLM_MAX_TOKENS,
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