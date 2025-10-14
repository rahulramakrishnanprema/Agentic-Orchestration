# Reviewer Agent MongoDB Storage Fix

## Problem
The Reviewer agent was failing to store data in MongoDB with the error:
```
MongoDB storage failed: MongoDB not available
```

While other agents (Planner, Developer) were successfully storing their data.

## Root Cause
The Reviewer agent was trying to store data in its own separate MongoDB collection (`MONGODB_REVIEWER_COLLECTION`) through the `store_review_in_mongodb()` function in `reviewer_tool.py`. However, it was NOT using the **shared performance tracker service** that other agents use.

### How Other Agents Store Data
- **Planner Agent**: Stores data via `performance_tracker.update_daily_metrics_after_pr()`
- **Developer Agent**: Stores data via `performance_tracker.update_daily_metrics_after_pr()`
- **Reviewer Agent (OLD)**: Tried to store ONLY in its own collection via `store_review_in_mongodb()`

The shared performance tracker updates the main collection (`MONGODB_COLLECTION_MATRIX`) which is properly initialized and working.

## Solution Applied

### Changes Made to `graph/reviewer_graph.py`

1. **Added Performance Tracker Import** (Line 11):
   ```python
   from services.performance_tracker import performance_tracker
   ```

2. **Updated `_node_store_results()` Function** (Lines 318-384):
   - Keeps the existing reviewer-specific MongoDB storage (for detailed review data)
   - **ADDED**: Integration with the shared performance tracker service
   - Now stores data in BOTH locations, just like other agents do

### How It Works Now

The Reviewer agent now performs a **dual storage strategy**:

1. **Reviewer-Specific Collection** (existing behavior):
   - Stores detailed review data (completeness, security, standards scores)
   - Uses `store_review_in_mongodb()` tool
   - Collection: `MONGODB_REVIEWER_COLLECTION`

2. **Shared Performance Tracker** (NEW - matches other agents):
   - Stores aggregated metrics for dashboard/reporting
   - Uses `performance_tracker.update_daily_metrics_after_pr()`
   - Collection: `MONGODB_COLLECTION_MATRIX`
   - Includes:
     - Agent metrics (ReviewerAgent tasks completed, tokens used, LLM model)
     - Quality scores (overall_score as sonarqube_score)
     - Daily aggregations

### Code Flow in `_node_store_results()`

```python
# 1. Store in reviewer-specific collection (existing)
result = store_review_in_mongodb.invoke({...})
reviewer_stored = result.get('success', False)

# 2. ALSO store in shared performance tracker (NEW)
if performance_tracker and performance_tracker.collection:
    agent_metrics = {
        "ReviewerAgent": {
            "Task_completed": 1,
            "LLM_model_used": os.getenv("REVIEWER_LLM_MODEL", "unknown"),
            "tokens_used": state['tokens_used']
        }
    }
    
    pr_data = {
        "issue_key": state['issue_key'],
        "pr_url": "",  # Reviewer doesn't create PRs
        "files_count": len(state.get('files', {}))
    }
    
    tracker_success = performance_tracker.update_daily_metrics_after_pr(
        pr_data=pr_data,
        agent_metrics=agent_metrics,
        sonarqube_score=state['overall_score'],
        success=state['approved'],
        thread_id=state['thread_id']
    )
```

## Benefits

1. **Consistency**: Reviewer now stores data the same way as other agents
2. **Reliability**: Uses the proven performance tracker that's already working
3. **Dashboard Integration**: Reviewer metrics now appear in the main dashboard
4. **Backward Compatible**: Keeps the existing reviewer-specific collection intact
5. **Graceful Degradation**: Falls back to reviewer-specific storage if tracker fails

## Testing

After deployment, you should see:
- ✅ `Performance tracker MongoDB storage successful` in logs
- ✅ `mongodb_stored: True` in the final state
- ✅ ReviewerAgent metrics appearing in the dashboard
- ✅ Daily metrics updated in `MONGODB_COLLECTION_MATRIX`

## Related Files Changed

- `graph/reviewer_graph.py` - Added performance tracker integration

## No Changes Needed To

- `tools/reviewer_tool.py` - Existing functions still work
- `agents/reviewer.py` - No changes needed
- `services/performance_tracker.py` - Already supports all agents
- Database configuration - Uses existing connections

## Date
Fixed: 2025-10-14

