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

        # Robust JSON parsing
        try:
            # Find JSON between curly braces
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                document = json.loads(json_match.group(0))
            else:
                # Clean and try again
                cleaned_content = content.strip()
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]
                document = json.loads(cleaned_content)

            # Validate required top-level fields
            required_fields = ['metadata', 'project_overview', 'implementation_plan', 'file_structure',
                               'technical_specifications', 'deployment_instructions']
            missing_fields = [field for field in required_fields if field not in document]

            if missing_fields:
                raise ValueError(f"Missing required fields in document: {', '.join(missing_fields)}")

            logger.info(f"[{thread_id}] Deployment document JSON generated successfully")

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