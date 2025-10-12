Analyze the following Pylint issues and calculate a quality score from 0-100.

**Pylint Issues (JSON format):**
{{{issues_json}}}

**Scoring Instructions:**
1. Parse the Pylint issues JSON
2. Count issues by severity:
   - **Error**: -10 points each (critical issues)
   - **Warning**: -5 points each (significant issues)
   - **Convention**: -2 points each (style issues)
   - **Refactor**: -3 points each (design issues)
   - **Info**: -1 point each (minor issues)
3. Start from 100 and subtract penalty points
4. Minimum score is 0, maximum is 100
5. If no issues, score is 100

**Output Format:**
Provide ONLY valid JSON with no additional text:

{
  "score": 78.5,
  "reasoning": "Detailed breakdown: X errors (-Y points), X warnings (-Y points), X convention issues (-Y points). Total: Z points deducted from 100. Main issues: [brief summary of top issues]"
}

Be strict and objective in scoring. The score should reflect actual code quality based on the issues found.
