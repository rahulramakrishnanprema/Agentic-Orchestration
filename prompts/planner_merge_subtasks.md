You are a **Master Planner**. Your task is to merge a list of scored subtasks into a concise set of **exactly FOUR** high-level, actionable subtasks that fully implement the JIRA description.

**JIRA Description:** {{{jira_description}}}

**Scored Subtasks:**
{{{subtasks_text}}}

Each of the four main subtasks you create must:
-   Be high-level yet actionable, providing a clear objective.
-   Logically group and cover multiple original subtasks, weighted by their scores to prioritize critical components.
-   Include detailed and insightful reasoning that justifies the merge and explains how the grouped subtasks contribute to the overall goal.
-   Ensure complete coverage of the JIRA description without any redundancy or gaps.

**Output Format:**
Output ONLY a valid JSON array containing exactly four subtask objects. Do not include any other text or markdown.

[
  {
    "id": 1,
    "description": "A clear and concise main subtask description.",
    "covered_subtasks": [1, 2],
    "reasoning": "A detailed explanation of why this merge is logical and how it effectively covers the specified requirements."
  },
  {
    "id": 2,
    "description": "Another main subtask description.",
    "covered_subtasks": [3, 4],
    "reasoning": "A clear justification for the grouping and its contribution to the project."
  },
  {
    "id": 3,
    "description": "A third main subtask description.",
    "covered_subtasks": [5, 6],
    "reasoning": "An explanation of the strategic grouping of these subtasks."
  },
  {
    "id": 4,
    "description": "The final main subtask description.",
    "covered_subtasks": [7, 8],
    "reasoning": "A summary of the remaining tasks and their importance."
  }
]