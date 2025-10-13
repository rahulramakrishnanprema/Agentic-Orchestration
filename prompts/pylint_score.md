# Pylint Code Quality Analysis and Scoring

You are analyzing Python code quality based on Pylint static analysis results.

## Context Information

{{{pylint_context}}}

## Scoring Guidelines

### Issue Severity Penalties (Start from 100 points)
- **Errors** (type: error): -10 points each - Critical issues that will cause runtime failures
- **Warnings** (type: warning): -5 points each - Significant issues that may cause bugs
- **Refactor** (type: refactor): -3 points each - Design/architecture improvements needed
- **Conventions** (type: convention): -2 points each - Code style and best practice violations

### Important Notes
1. **Cosmetic issues are already filtered out** (line-too-long, trailing-whitespace, missing-final-newline)
2. Only **significant issues** affecting code quality are included
3. Even with 0 issues, provide thoughtful reasoning about the code quality
4. Score should reflect actual code quality, not just absence of issues

### Scoring Formula
```
Final Score = 100 - (Errors × 10) - (Warnings × 5) - (Refactors × 3) - (Conventions × 2)
Minimum: 0
Maximum: 100
```

### Score Interpretation
- **90-100**: Excellent code quality, minimal or no issues
- **80-89**: Good code quality, minor issues only
- **70-79**: Acceptable code quality, some improvements needed
- **60-69**: Below average, multiple issues need attention
- **Below 60**: Poor code quality, significant refactoring required

## Special Cases

### If 0 Significant Issues:
- **DO NOT automatically give 100/100**
- Consider: code complexity, file count, overall structure
- Typical range: 85-95 (excellent but not perfect)
- Score 100 only if code is truly exceptional

### If Only Convention Issues:
- These are still important (not cosmetic)
- Score should be 80-90 range
- Explain what conventions are violated

### If Errors Present:
- Score should be below 70
- Each error is critical
- Emphasize severity in reasoning

## Output Format

Provide ONLY valid JSON with no additional text or markdown:

```json
{
  "score": 85.0,
  "reasoning": "Analyzed {{{files_analyzed}}} Python files. Found {{{total_issues}}} significant issues after filtering cosmetic problems. Breakdown: {{{errors}}} errors (-X points), {{{warnings}}} warnings (-Y points), {{{conventions}}} conventions (-Z points), {{{refactors}}} refactors (-W points). Total penalty: -15 points from 100. Main concerns: [list top 2-3 specific issues]. Overall: Good code quality with minor improvements needed.",
  "mistakes": []
}
```

## Example Scoring

### Example 1: No Issues
```json
{
  "score": 92.0,
  "reasoning": "Analyzed 5 Python files with 0 significant issues found. Code follows Python best practices, proper error handling, and clean structure. Minor deduction for not being perfect - there's always room for improvement in documentation and edge case handling.",
  "mistakes": []
}
```

### Example 2: Some Issues
```json
{
  "score": 73.0,
  "reasoning": "Analyzed 10 files. Found 2 errors (-20), 3 warnings (-15), 1 refactor (-3), 5 conventions (-10). Total: -48 points. Main issues: undefined variable 'result' in api.py, unused import in utils.py, missing exception handling. Code needs attention to error handling and imports.",
  "mistakes": []
}
```

### Example 3: Many Issues
```json
{
  "score": 45.0,
  "reasoning": "Analyzed 8 files with severe quality issues. Found 5 errors (-50), 2 warnings (-10), 0 refactors, 15 conventions (-30). Total: -90 points capped at minimum viable score. Critical: undefined variables, import errors, inconsistent returns. Requires significant refactoring.",
  "mistakes": []
}
```

Now analyze the provided Pylint results and give your score.
