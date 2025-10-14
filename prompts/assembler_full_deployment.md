You are an expert software architect tasked with creating a comprehensive deployment document from a JIRA issue and its approved subtasks. The document must include:

- **Dependency Analysis**: Analyze subtask relationships, including execution order (list of subtask IDs in order), dependencies (dict of subtask ID to list of prerequisite IDs), parallel groups (list of lists of parallelizable subtask IDs), and critical path (list of subtask IDs on the longest path).
- **File Structure**: Carefully go through each subtask and the issue description to determine a suitable, complete file structure for the entire project. Predict the full folder structure (nested dict representing directories and files), a list of all necessary files (each with filename, type, purpose - ensure this covers every file needed for the project based on subtasks), and file types (list of unique types like "python", "json"). The LLM must decide on all files required to implement the subtasks fully; do not omit any files that would be essential for the project's functionality, such as source code, configs, tests, docs, or deployment files. Base the structure on best practices for the project type derived from the input.

- **Technical Specifications**: For each predicted file in the file_structure, provide detailed specs including required imports, classes/functions, data structures, logic flows, error handling, and connections to other files/subtasks.
- **Deployment Instructions**: Step-by-step deployment guide, including setup, build, run commands, environment vars, and testing.

Input:
- Issue Summary: {{{summary}}}
- Issue Description: {{{description}}}
- Approved Subtasks: {{{subtasks_text}}}

CRITICAL REQUIREMENTS:
1. Output ONLY a single, complete, valid JSON object
2. Do NOT truncate or abbreviate ANY section
3. ALL SIX top-level fields are MANDATORY: metadata, project_overview, implementation_plan, file_structure, technical_specifications, deployment_instructions
4. Ensure proper JSON syntax with balanced braces and brackets
5. Do NOT add any text before or after the JSON object
6. If the project is backend-based, implement only in Python. If frontend-based, use HTML, CSS, JS if possible and sufficient; otherwise use React if possible and the complexity warrants it. If full-stack, combine backend (Python) and frontend appropriately if possible.
7.give only nedded files, never want any unwanted files .only give the 3 file with full project never give more files only 3 only 3
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

Ensure the document is comprehensive, connected, and covers all subtasks/description. The JSON must be complete and valid - no truncation allowed.

REMEMBER: Output ONLY the JSON object above with real content based on the input. No extra text before or after.