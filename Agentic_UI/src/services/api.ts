// src/services/api.ts
// Use environment variable for API URL, fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : 'http://localhost:5173/api';

console.log('API Base URL:', API_BASE_URL); // For debugging

// Add connection timeout and retry configuration
const REQUEST_TIMEOUT = 10000; // 10 seconds
const MAX_RETRIES = 3; // Helper function for timeout handling
const timeout = (ms: number): Promise<never> => {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Request timeout')), ms);
  });
}; // Helper function for retry logic
const fetchWithRetry = async (url: string, options: RequestInit = {}, retries = MAX_RETRIES): Promise<Response> => {
  try {
    const response = await Promise.race([
      fetch(url, options),
      timeout(REQUEST_TIMEOUT)
    ]);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response;
  } catch (error) {
    if (retries > 0) {
      console.warn(`Retrying request... (${retries} attempts left)`);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second before retry
      return fetchWithRetry(url, options, retries - 1);
    }
    throw error;
  }
};

export const api = {
  async getStatus() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/status`);
      const data = await response.json();
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response format from server');
      }
      return {
        system_status: data.system_status || 'unknown',
        active_issues: data.active_issues || 0,
        queue_size: data.queue_size || 0,
        running_tasks: data.running_tasks || 0,
        agents_ready: data.agents_ready || {
          task_agent: false,
          developer_agent: false,
          reviewer_agent: false,
          rebuilder_agent: false,
          jira_client: false
        },
        configuration: data.configuration || {
          model: 'unknown',
          mcp_endpoint: 'unknown',
          project_key: 'unknown',
          review_threshold: 0
        },
        current_stage: data.current_stage || 'idle',
        system_running: data.system_running || false,
        timestamp: data.timestamp || new Date().toISOString()
      };
    } catch (err) {
      console.error('Failed to fetch system status:', err);
      throw new Error(`Failed to connect to server: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  },

  async getStats() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/stats`);
      const data = await response.json();
      return {
        totalPullRequests: data.totalPullRequests || data.code_prs_created || data.pull_requests_created || 0,
        prAccepted: data.prAccepted || data.pr_accepted || data.successful_reviews || 0,
        tokensUsed: data.tokensUsed || data.tokens_used || 0,
        tasksCompleted: data.tasksCompleted || data.tasks_completed || 0,
        tasksFailed: data.tasksFailed || data.tasks_failed || 0,
        tasksPending: data.tasksPending || data.tasks_pending || 0,
        tasksMovedToHITL: data.tasksMovedToHITL || data.tasks_moved_to_hitl || 0,
        averageSonarQubeScore: data.averageSonarQubeScore || data.average_sonar_score || 0,
        averageReviewScore: data.averageReviewScore || data.average_review_score || 0,  // NEW: Add reviewer score
        successRate: data.successRate || 0,
        taskagent_generations: data.taskagent_generations || 0,
        developer_generations: data.developer_generations || 0,
        reviewer_generations: data.reviewer_generations || 0,
        rebuilder_generations: data.rebuilder_generations || 0,
        planner_tokens: data.planner_tokens || 0,
        developer_tokens: data.developer_tokens || 0,
        reviewer_tokens: data.reviewer_tokens || 0,
        rebuilder_tokens: data.rebuilder_tokens || 0,
        last_updated: data.last_updated || new Date().toISOString(),
        system_status: data.system_status || 'unknown'
      };
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
      throw new Error(`Failed to fetch statistics: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async getActivity() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/activity`);
      const data = await response.json();
      const activities = data.activity || data || [];
      return {
        activity: Array.isArray(activities) ? activities : []
      };
    } catch (error) {
      console.error('Failed to fetch activity logs:', error);
      return { activity: [] };
    }
  },

  async getConfig() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/config`);
      const data = await response.json();
      return {
        token: data.token || '',
        pullRequest: data.pullRequest || `PR-${(data.pull_requests_created || 0) + 1}`
      };
    } catch (error) {
      console.error('Failed to fetch configuration:', error);
      return { token: '', pullRequest: 'PR-1' };
    }
  },

  async getHealth() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch health status:', error);
      return {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        uptime: '0s',
        version: 'unknown'
      };
    }
  },

  async startAutomation(projectKey: string) {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/start-automation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ project_key: projectKey }),
      });
      const data = await response.json();
      return {
        success: data.success || false,
        status: data.status || 'unknown',
        project_key: data.project_key || projectKey,
        issues_queued: data.issues_queued || 0,
        total_todo_issues: data.total_todo_issues || 0,
        queue_position: data.queue_position || 0,
        currently_running: data.currently_running || 0,
        timestamp: data.timestamp || new Date().toISOString(),
        message: data.message || 'Automation started'
      };
    } catch (error) {
      console.error('Failed to start automation:', error);
      throw new Error(`Failed to start automation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async stopSystem() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/stop-automation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      return {
        success: data.success || false,
        message: data.message || 'System stopped',
        stopped_at: data.stopped_at || new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to stop system:', error);
      throw new Error(`Failed to stop system: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async resetStats() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/reset-stats`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      return {
        success: data.success || false,
        message: data.message || 'Statistics reset',
        reset_time: data.reset_time || new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to reset statistics:', error);
      throw new Error(`Failed to reset statistics: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async saveConfig(serviceId: string, config: Record<string, string>) {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/config/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          service: serviceId,
          config: config,
          timestamp: new Date().toISOString()
        }),
      });
      const data = await response.json();
      return {
        success: data.success || false,
        message: data.message || 'Configuration saved',
        service: data.service || serviceId,
        saved_at: data.saved_at || new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to save configuration:', error);
      throw new Error(`Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async testConnection(): Promise<boolean> {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/health`, {}, 1);
      const data = await response.json();
      return data.status === 'healthy';
    } catch {
      return false;
    }
  },

  async getSystemInfo() {
    try {
      const [status, stats, health] = await Promise.all([
        this.getStatus(),
        this.getStats(),
        this.getHealth()
      ]);
      return {
        status,
        stats,
        health,
        connected: true,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        connected: false,
        error: error instanceof Error ? error.message : 'Connection failed',
        timestamp: new Date().toISOString()
      };
    }
  },

  // NEW PERFORMANCE ENDPOINTS
  async getPerformanceData() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/performance-data`);
      const data = await response.json();
      return data.performance_data || [];
    } catch (error) {
      console.error('Failed to fetch performance data:', error);
      return [];
    }
  },

  async getWeeklyPerformance() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/performance/weekly`);
      const data = await response.json();
      return data.weekly_data || [];
    } catch (error) {
      console.error('Failed to fetch weekly performance:', error);
      return [];
    }
  },

  async getRealTimeMetrics() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/performance/realtime`);
      const data = await response.json();
      return data.data || {};
    } catch (error) {
      console.error('Failed to fetch real-time metrics:', error);
      return {};
    }
  },

  async getAgentPerformance() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/performance/agents`);
      const data = await response.json();
      return data.agent_performance || [];
    } catch (error) {
      console.error('Failed to fetch agent performance:', error);
      return [];
    }
  },

  // NEW: Get current session agents
  async getCurrentAgents() {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/current-agents`);
      const data = await response.json();
      return data.current_agents || [];
    } catch (error) {
      console.error('Failed to fetch current agents:', error);
      return [];
    }
  }
};