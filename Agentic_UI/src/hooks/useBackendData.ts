// File: src/hooks/useBackendData.ts
import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Agent, JiraIssue, ActivityLog, Metrics, PerformanceData } from '../types/dashboard';

interface BackendStatus {
  system_status: string;
  active_issues: number;
  queue_size: number;
  running_tasks: number;
  agents_ready: {
    task_agent: boolean;
    assembler_agent: boolean;
    developer_agent: boolean;
    reviewer_agent: boolean;
    rebuilder_agent: boolean;
    jira_client: boolean;
  };
  configuration: {
    model: string;
    mcp_endpoint: string;
    project_key: string;
    review_threshold: number;
  };
  current_stage: string;
  system_running: boolean;
  timestamp: string;
}

interface BackendStats {
  totalPullRequests: number;
  prAccepted: number;
  tokensUsed: number;
  tasksCompleted: number;
  tasksFailed: number;
  tasksPending: number;
  tasksMovedToHITL: number;
  averageSonarQubeScore: number;
  successRate: number;
  taskagent_generations: number;
  developer_generations: number;
  reviewer_generations: number;
  rebuilder_generations: number;
  last_updated: string;
  system_status: string;
}

interface BackendActivity {
  activity: Array<{
    id: string;
    timestamp: string;
    agent: string;
    action: string;
    details: string;
    status: 'info' | 'success' | 'warning' | 'error';
    issueId?: string;
  }>;
}

export const useBackendData = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [currentAgents, setCurrentAgents] = useState<Agent[]>([]);  // For current session agents
  const [currentIssue, setCurrentIssue] = useState<JiraIssue | null>(null);
  const [workflowStage, setWorkflowStage] = useState('task-fetch');
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [metrics, setMetrics] = useState<Metrics>({
    totalPullRequests: 0,
    prAccepted: 0,
    tokensUsed: 0,
    tasksCompleted: 0,
    tasksFailed: 0,
    tasksPending: 0,
    tasksMovedToHITL: 0,
    averageSonarQubeScore: 0,
    successRate: 0,
    taskagent_generations: 0,
    developer_generations: 0,
    reviewer_generations: 0,
    rebuilder_generations: 0
  });
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [isSystemRunning, setIsSystemRunning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch system status
  const fetchStatus = useCallback(async () => {
    try {
      const status: BackendStatus = await api.getStatus();
      setIsConnected(true);
      setIsSystemRunning(status.system_running);
      setWorkflowStage(status.current_stage);
      setError(null);
      // Convert backend agents to UI format
      const backendAgents: Agent[] = [
        {
          id: '1',
          name: 'PlannerAgent',
          status: status.agents_ready.task_agent ? 'active' : 'inactive',
          lastActivity: new Date(),
          tasksProcessed: 0,
          llmModel: status.configuration.model,
          tokensConsumed: 0
        },
        {
          id: '2',
          name: 'AssemblerAgent',  // Explicitly include Assembler
          status: status.agents_ready.assembler_agent ? 'active' : 'inactive',
          lastActivity: new Date(),
          tasksProcessed: 0,
          llmModel: status.configuration.model,
          tokensConsumed: 0
        },
        {
          id: '3',
          name: 'DeveloperAgent',
          status: status.agents_ready.developer_agent ? 'active' : 'inactive',
          lastActivity: new Date(),
          tasksProcessed: 0,
          llmModel: status.configuration.model,
          tokensConsumed: 0
        },
        {
          id: '4',
          name: 'ReviewerAgent',
          status: status.agents_ready.reviewer_agent ? 'active' : 'inactive',
          lastActivity: new Date(),
          tasksProcessed: 0,
          llmModel: status.configuration.model,
          tokensConsumed: 0
        }
      ];
      setAgents(backendAgents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
      setIsConnected(false);
    }
  }, []);

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const stats: BackendStats = await api.getStats();
      setMetrics({
        totalPullRequests: stats.totalPullRequests,
        prAccepted: stats.prAccepted,
        tokensUsed: stats.tokensUsed,
        tasksCompleted: stats.tasksCompleted,
        tasksFailed: stats.tasksFailed,
        tasksPending: stats.tasksPending,
        tasksMovedToHITL: stats.tasksMovedToHITL,
        averageSonarQubeScore: stats.averageSonarQubeScore,
        successRate: stats.successRate,
        taskagent_generations: stats.taskagent_generations,
        developer_generations: stats.developer_generations,
        reviewer_generations: stats.reviewer_generations,
        rebuilder_generations: stats.rebuilder_generations
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats');
    }
  }, []);

  // NEW: Fetch current session agent performance (in-memory)
  const fetchCurrentAgentPerformance = useCallback(async () => {
    try {
      const currentAgentData = await api.getCurrentAgents();
      setCurrentAgents(currentAgentData.map(agent => ({
        id: agent.agent,  // Use agent name as id
        name: agent.agent,
        status: 'active',  // Assume active for current
        lastActivity: new Date(),
        tasksProcessed: agent.tasks_processed,  // Real data
        llmModel: agent.model_used,
        tokensConsumed: agent.tokens_used,  // Real data
        successRate: agent.success_rate  // Real data
      })));
    } catch (err) {
      console.error('Failed to fetch current agent performance:', err);
    }
  }, []);

  // Fetch historical agent performance from MongoDB
  const fetchAgentPerformance = useCallback(async () => {
    try {
      const agentData = await api.getAgentPerformance();
      setAgents(prevAgents => prevAgents.map(agent => {
        const perf = agentData.find(p => p.agent === agent.name) || {};
        return {
          ...agent,
          tasksProcessed: perf.tasks_processed || 0,
          tokensConsumed: perf.tokens_used || 0,
          successRate: perf.success_rate || 0,
          llmModel: perf.model_used || agent.llmModel
        };
      }));
    } catch (err) {
      console.error('Failed to fetch agent performance:', err);
    }
  }, []);

  // Fetch activity logs
  const fetchActivity = useCallback(async () => {
    try {
      const activityData: BackendActivity = await api.getActivity();
      const formattedLogs: ActivityLog[] = activityData.activity.map(activity => ({
        id: activity.id,
        timestamp: new Date(activity.timestamp),
        agent: activity.agent,
        action: activity.action,
        details: activity.details,
        status: activity.status,
        issueId: activity.issueId
      }));
      setActivityLogs(formattedLogs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch activity');
    }
  }, []);

  // Fetch performance data from MongoDB (no mock fallback)
  const fetchPerformanceData = useCallback(async () => {
    try {
      const performanceData = await api.getPerformanceData();
      setPerformanceData(performanceData);
    } catch (err) {
      console.error('Failed to fetch performance data:', err);
      setPerformanceData([]);  // Set empty on error - no mocks
    }
  }, []);

  // Start system
  const startSystem = useCallback(async (projectKey?: string) => {
    try {
      const result = await api.startAutomation(projectKey || 'DEFAULT');
      setIsSystemRunning(true);
      setError(null);
      // Refresh data after starting
      await Promise.all([fetchStatus(), fetchStats(), fetchActivity()]);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start system');
      throw err;
    }
  }, [fetchStatus, fetchStats, fetchActivity]);

  // Stop system
  const stopSystem = useCallback(async () => {
    try {
      await api.stopSystem();
      setIsSystemRunning(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop system');
      throw err;
    }
  }, []);

  // Reset statistics
  const resetStats = useCallback(async () => {
    try {
      await api.resetStats();
      await fetchStats();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset stats');
      throw err;
    }
  }, [fetchStats]);

  // Initial data fetch and polling with shorter interval for today's data
  useEffect(() => {
    const fetchAllData = async () => {
      await Promise.all([
        fetchStatus(),
        fetchStats(),
        fetchCurrentAgentPerformance(),
        fetchAgentPerformance(),
        fetchActivity(),
        fetchPerformanceData()
      ]);
    };

    // Initial fetch
    fetchAllData();

    // Polling interval - more frequent for active system
    const interval = setInterval(fetchAllData, isSystemRunning ? 3000 : 5000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchStats, fetchCurrentAgentPerformance, fetchAgentPerformance, fetchActivity, fetchPerformanceData, isSystemRunning]);

  return {
    agents,  // Historical agents (MongoDB)
    currentAgents,  // Current session agents (in-memory)
    currentIssue,
    workflowStage,
    activityLogs,
    metrics,
    performanceData,
    isSystemRunning,
    isConnected,
    error,
    startSystem,
    stopSystem,
    resetStats
  };
};