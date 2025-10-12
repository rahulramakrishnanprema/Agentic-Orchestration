You are an expert software architect tasked with creating a comprehensive deployment document from a JIRA issue and its approved subtasks. The document must include:

- **Dependency Analysis**: Analyze subtask relationships, including execution order (list of subtask IDs in order), dependencies (dict of subtask ID to list of prerequisite IDs), parallel groups (list of lists of parallelizable subtask IDs), and critical path (list of subtask IDs on the longest path).
- **File Structure**: Predict the complete folder structure (nested dict), list of files (each with filename, type, purpose), and file types (list of unique types like "python", "json").
- **Technical Specifications**: For each predicted file, provide detailed specs including required imports, classes/functions, data structures, logic flows, error handling, and connections to other files/subtasks.
- **Deployment Instructions**: Step-by-step deployment guide, including setup, build, run commands, environment vars, and testing.

Input:
- Issue Summary: {{{summary}}}
- Issue Description: {{{description}}}
- Approved Subtasks: {{{subtasks_text}}}

Output a SINGLE JSON object with this exact structure (no extra text or markdown):

{
  "metadata": {
    "issue_key": "string",
    "issue_summary": "string",
    "created_at": "ISO datetime",
    "version": "1.0"
  },
  "project_overview": {
    "description": "string",
    "project_type": "e.g., web app, API",
    "architecture": "e.g., MVC, microservices"
  },
  "implementation_plan": {
    "subtasks": [array of original subtasks],
    "execution_order": [array of subtask IDs in order],
    "dependencies": {"subtask_id": [array of prerequisite IDs]},
    "parallel_groups": [[array of parallel subtask IDs]],
    "critical_path": [array of subtask IDs]
  },
  "file_structure": {
    "files": [{"filename": "string", "type": "string", "purpose": "string"}],
    "folder_structure": {"root": {"subfolder": {}}},
    "file_types": ["array of unique types"]
  },
  "technical_specifications": {
    "filename.py": {
      "imports": ["list of imports"],
      "classes": ["list of class names with descriptions"],
      "functions": ["list of function names with params/returns/descriptions"],
      "data_structures": ["descriptions"],
      "logic_flows": ["step-by-step logic"],
      "error_handling": ["descriptions"],
      "connections": ["to other files/subtasks"]
    }
  },
  "deployment_instructions": {
    "setup": ["steps"],
    "build": ["commands"],
    "run": ["commands"],
    "environment_vars": {"VAR": "description"},
    "testing": ["steps"]
  }
}

Ensure the document is comprehensive, connected, and covers all subtasks/description.