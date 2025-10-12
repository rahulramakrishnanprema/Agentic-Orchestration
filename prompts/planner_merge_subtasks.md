Merge these scored subtasks into exactly THREE main subtasks that fully implement the JIRA description:
JIRA Description: {{{jira_description}}}

Scored Subtasks:
{{{subtasks_text}}}

Each main subtask should:
- Be high-level but actionable
- Cover multiple original subtasks, weighted by scores
- Include detailed reasoning
- Ensure complete coverage without redundancy

Output as JSON array:
[
  {{
    "id": 1,
    "description": "main subtask description",
    "covered_subtasks": [1, 2],
    "reasoning": "why this merge and coverage"
  }},
  {{
    "id": 2,
    "description": "main subtask description",
    "covered_subtasks": [3],
    "reasoning": "why this merge and coverage"
  }},
  {{
    "id": 3,
    "description": "main subtask description",
    "covered_subtasks": [4, 5],
    "reasoning": "why this merge and coverage"
  }}
]