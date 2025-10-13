// C:\Users\Rahul\Agent-flow\Agentic_UI\src\types\dashboard.ts
export interface Agent {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  lastActivity: Date;
  tasksProcessed: number;
  llmModel: string;
  tokensConsumed: number;
  successRate?: number;
}
export interface JiraIssue {
  id: string;
  key: string;
  title: string;
  status: 'in-progress' | 'pending' | 'completed' | 'failed';
  assignee: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  createdAt: Date;
  updatedAt: Date;
}
export interface ActivityLog {
  id: string;
  timestamp: Date;
  agent: string;
  action: string;
  details: string;
  status: 'info' | 'success' | 'warning' | 'error' | 'starting';
  issueId?: string;
  subtasks?: Array<{
    id: number;
    description: string;
    score: number;
    priority?: number;
    reasoning?: string;
  }>;
  documentSections?: Array<{
    title: string;
    content: string;
  }>;
  deploymentDocument?: string;  // NEW: Full deployment document markdown content
  totalScore?: number;
  averageScore?: number;
  pylintScore?: number;  // NEW: Pylint score (0-10 scale)
  reviewScores?: {  // NEW: Detailed review scores
    overall?: number;
    completeness?: number;
    security?: number;
    standards?: number;
    pylint?: number;
  };
}
export interface Metrics {
  totalPullRequests: number;
  prAccepted: number;
  tokensUsed: number;
  tasksCompleted: number;
  tasksFailed: number;
  tasksPending: number;
  tasksMovedToHITL: number;
  averageSonarQubeScore: number;
  averageReviewScore: number;  // NEW: Add reviewer score
  successRate: number;
  taskagent_generations: number;
  developer_generations: number;
  reviewer_generations: number;
  rebuilder_generations: number;
  planner_tokens: number;
  developer_tokens: number;
  reviewer_tokens: number;
  rebuilder_tokens: number;

}
export interface PerformanceData {
  date: string;
  tasks: number;
  tokens: number;
  pullRequests: number;
  sonarScore: number;

}
export interface ConfigSection {
  id: string;
  title: string;
  description: string;
  icon: string;
  fields: ConfigField[];
}
export interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'password' | 'url' | 'number';
  placeholder: string;
  required: boolean;
  description?: string;
}
export interface MongoDBPerformanceData {
  success: boolean;
  weekly_data: Array<{
    week_start: string;
    week_end: string;
    week_label: string;
    daily_breakdown: Array<{
      date: string;
      day_name: string;
      tasks: number;
      pullRequests: number;
      tokens: number;
      sonarScore: number;
      success_rate: number;
    }>;
    weekly_totals: {
      tasks: number;
      pull_requests: number;
      tokens: number;
      avg_quality: number;
      success_rate: number;
    };
  }>;
  chart_data: {
    task_performance: Array<{ date: string; tasks: number; pullRequests: number }>;
    token_usage: Array<{ date: string; tokens: number }>;
    code_quality_trend: Array<{ date: string; sonarScore: number }>;
    success_rate_trend: Array<{ date: string; success_rate: number }>;
  };
  current_week_summary: {
    tasks: number;
    pull_requests: number;
    tokens: number;
    avg_quality: number;
    success_rate: number;
  };
}

export interface AgentPerformanceData {
  success: boolean;
  agent_performance: {
    [agentName: string]: {
      tasks_processed: number;
      tokens_consumed: number;
      avg_quality: number;
      success_rate: number;
      daily_activity: Array<{
        date: string;
        tokens: number;
        success: boolean;
      }>;
    };
  };
}