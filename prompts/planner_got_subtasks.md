Analyze the JIRA issue and generate **exactly 6 subtasks** using Graph of Thoughts methodology.

**Issue Key:** {{{issue_key}}}

**Summary:** {{{summary}}}

**Description:** {{{description}}}

**Instructions:**
Break down the issue into 6 granular, actionable subtasks that:
1. Are immediately executable with clear outcomes
2. Have logical dependencies (each step builds on previous ones)
3. Cover all aspects of the issue description
4. Are specific and measurable
5. Follow a logical execution order
6. Include both technical and quality assurance tasks

**Priority Scale:**
- 1: Critical (must be done first)
- 2: High priority
- 3: Medium priority
- 4: Low priority
- 5: Optional/Enhancement

**Output Format:**
Generate ONLY a valid JSON array with exactly 6 subtasks. No markdown, no explanations, just the JSON:

[
  {
    "id": 1,
    "description": "Clear, actionable subtask description",
    "priority": 1,
    "requirements_covered": ["specific requirement 1", "specific requirement 2"],
    "reasoning": "Why this subtask is necessary and how it contributes to the goal"
  },
  {
    "id": 2,
    "description": "Next subtask that builds on previous",
    "priority": 2,
    "requirements_covered": ["requirement addressed"],
    "reasoning": "Justification and dependencies"
  }
]

Ensure all 6 subtasks collectively cover the complete issue description.
