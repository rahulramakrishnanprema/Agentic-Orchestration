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
            f"- {st.get('description', '')}"
            for st in subtasks
        ])

        prompt = prompt_loader.format(
            "assembler_full_deployment",
            summary=summary,
            description=description,
            subtasks_text=subtasks_text
        )

        content, tokens = call_llm(prompt, agent_name="assembler")

        # Robust JSON parsing with better error handling
        try:
            # First, try to find complete JSON between curly braces
            # Use non-greedy matching to avoid catching incomplete JSON
            json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', content, re.DOTALL)

            if not json_match:
                # Try to find JSON markers and extract
                json_match = re.search(r'\{.*\}', content, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)

                # Validate JSON is complete (check for balanced braces)
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')

                if open_braces != close_braces:
                    logger.warning(f"[{thread_id}] JSON appears truncated: {open_braces} open braces, {close_braces} close braces")
                    logger.warning(f"[{thread_id}] Response length: {len(content)} characters")

                    # Try to salvage by finding last complete object
                    # Find the position of the last valid closing brace
                    brace_depth = 0
                    last_valid_pos = -1
                    for i, char in enumerate(json_str):
                        if char == '{':
                            brace_depth += 1
                        elif char == '}':
                            brace_depth -= 1
                            if brace_depth == 0:
                                last_valid_pos = i + 1
                                break

                    if last_valid_pos > 0:
                        json_str = json_str[:last_valid_pos]
                        logger.info(f"[{thread_id}] Attempting to parse truncated JSON (truncated to {last_valid_pos} chars)")
                    else:
                        raise ValueError("JSON is severely truncated and cannot be salvaged")

                document = json.loads(json_str)
            else:
                # Clean and try parsing the entire content
                cleaned_content = content.strip()
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]
                if cleaned_content.startswith('```'):
                    cleaned_content = cleaned_content[3:]
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]
                cleaned_content = cleaned_content.strip()
                document = json.loads(cleaned_content)

            # Validate required top-level fields
            required_fields = ['metadata', 'project_overview', 'implementation_plan', 'file_structure',
                               'technical_specifications', 'deployment_instructions']
            missing_fields = [field for field in required_fields if field not in document]

            if missing_fields:
                logger.warning(f"[{thread_id}] Missing fields: {', '.join(missing_fields)}")
                # Add default empty structures for missing fields
                for field in missing_fields:
                    if field == 'metadata':
                        document['metadata'] = {
                            "issue_key": issue_data.get('key', 'UNKNOWN'),
                            "issue_summary": issue_data.get('summary', ''),
                            "created_at": datetime.now().isoformat(),
                            "version": "1.0"
                        }
                    elif field == 'file_structure':
                        # Create default file structure based on subtasks
                        logger.warning(f"[{thread_id}] Creating default file structure from subtasks")
                        document['file_structure'] = {
                            "file_types": ["python", "javascript", "html", "css"],
                            "files": [
                                {
                                    "filename": f"main.py",
                                    "type": "python",
                                    "description": "Main application file"
                                },
                                {
                                    "filename": f"config.py",
                                    "type": "python",
                                    "description": "Configuration file"
                                }
                            ]
                        }
                    elif field == 'technical_specifications':
                        document['technical_specifications'] = {
                            "main.py": {
                                "purpose": "Main application entry point",
                                "dependencies": [],
                                "functions": []
                            }
                        }
                    elif field == 'implementation_plan':
                        document['implementation_plan'] = {
                            "phases": [
                                {
                                    "name": "Initial Setup",
                                    "tasks": subtasks_text.split('\n')[:3]
                                }
                            ]
                        }
                    else:
                        document[field] = {}
                logger.info(f"[{thread_id}] Added default structures for missing fields")

            # Additional validation: ensure file_structure has the required nested fields
            if 'file_structure' in document:
                file_structure = document['file_structure']
                if not file_structure.get('files') or len(file_structure.get('files', [])) == 0:
                    logger.warning(f"[{thread_id}] file_structure.files is empty, adding default files")
                    file_structure['files'] = [
                        {
                            "filename": f"{issue_data.get('key', 'app').lower()}_main.py",
                            "type": "python",
                            "description": f"Main application file for {issue_data.get('summary', 'project')}"
                        }
                    ]
                if not file_structure.get('file_types'):
                    file_structure['file_types'] = ["python"]

            logger.info(f"[{thread_id}] Deployment document JSON parsed successfully")

            # Render MD using LLM and template
            json_document = json.dumps(document, indent=2)
            md_prompt = prompt_loader.format(
                "assembler_md_render",
                json_document=json_document
            )
            md_content, md_tokens = call_llm(md_prompt, agent_name="assembler")
            tokens += md_tokens

            # Clean MD content
            md_content = md_content.strip()
            if md_content.startswith('```markdown'):
                md_content = md_content[10:]
            if md_content.endswith('```'):
                md_content = md_content[:-3]
            md_content = md_content.strip()

            # Store MD locally
            local_folder = "deployment_documents"
            os.makedirs(local_folder, exist_ok=True)
            md_path = os.path.join(local_folder, f"{issue_data.get('key', 'UNKNOWN')}.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"[{thread_id}] Deployment document MD saved to {md_path}")

            return {
                "success": True,
                "document": document,
                "markdown": md_content,
                "tokens_used": tokens
            }
        except json.JSONDecodeError as je:
            logger.error(f"[{thread_id}] JSON parsing error: {je}")
            logger.error(f"[{thread_id}] Response content: {content}")
            raise ValueError(f"Failed to parse deployment document JSON: {str(je)}")
        except Exception as e:
            logger.error(f"[{thread_id}] Document validation error: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"[{thread_id}] Document generation failed: {str(e)}")
        return {"success": False, "error": str(e), "tokens_used": 0}