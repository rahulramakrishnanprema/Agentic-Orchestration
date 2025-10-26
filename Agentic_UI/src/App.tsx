// File: src/App.tsx
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Square,
  GitPullRequest,
  Zap,
  CheckCircle,
  XCircle,
  TrendingUp,
  GitMerge,
  Users,
  Clock,
  RefreshCw
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { MetricCard } from './components/MetricCard';
import { AgentCard } from './components/AgentCard';
import { AgentPerformanceCard } from './components/AgentPerformanceCard';
import { ActivityLog } from './components/ActivityLog';
import { WorkflowTracker } from './components/WorkflowTracker';
import { PerformanceCharts } from './components/PerformanceCharts';
import { AgentPerformanceCharts } from './components/AgentPerformanceCharts';
import { SettingsPage } from './components/SettingsPage';
import { PasswordProtection } from './components/PasswordProtection';
import { useBackendData } from './hooks/useBackendData';
import { SystemStatus } from './components/SystemStatus';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const {
    agents,
    currentAgents,  // NEW: Use for Agents tab
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
  } = useBackendData();

  useEffect(() => {
    const auth = sessionStorage.getItem('authenticated');
    if (auth === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleAuthenticated = () => {
    setIsAuthenticated(true);
  };

  const handleSystemControl = async () => {
    if (isProcessing) return;
    try {
      setIsProcessing(true);
      setStatusMessage('');
      if (isSystemRunning) {
        await stopSystem();
        toast.success('System stopped successfully');
        setStatusMessage('System stopped successfully');
      } else {
        const result = await startSystem('DEFAULT');
        if (result?.success) {
          toast.success(`Started processing: ${result.issues_queued} issues queued`);
          setStatusMessage(`Started processing: ${result.issues_queued} issues queued`);
        } else {
          toast.error(result?.message || 'Failed to start system');
          setStatusMessage(result?.message || 'System started');
        }
      }
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : 'Operation failed'}`);
      setStatusMessage(`Error: ${err instanceof Error ? err.message : 'Operation failed'}`);
    } finally {
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(''), 3000);
    }
  };

  const handleResetStats = async () => {
    try {
      await resetStats();
      toast.success('Statistics reset successfully');
      setStatusMessage('Statistics reset successfully');
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (err) {
      toast.error(`Error resetting stats: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatusMessage(`Error resetting stats: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setTimeout(() => setStatusMessage(''), 3000);
    }
  };

  const getSystemButtonConfig = () => {
    if (isProcessing) return { text: 'Processing...', icon: RefreshCw, color: 'bg-yellow-600 hover:bg-yellow-700', disabled: true, animate: true };
    if (isSystemRunning) return { text: 'Stop System', icon: Square, color: 'bg-red-600 hover:bg-red-700', disabled: false, animate: false };
    return { text: 'Start Automation', icon: Play, color: 'bg-green-600 hover:bg-green-700', disabled: false, animate: false };
  };

  const buttonConfig = getSystemButtonConfig();
  const ButtonIcon = buttonConfig.icon;

  const formatTokens = (tokens: number) => {
    // Validate token value - if unrealistic, return 0
    if (!tokens || tokens < 0 || tokens > 10000000) {
      return '0';
    }

    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  const renderMainContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="space-y-6"
          >
            <SystemStatus isConnected={isConnected} isSystemRunning={isSystemRunning} error={error} />
            <div className="flex items-center justify-between">
              <div>
                <motion.h1
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                  className="text-2xl font-bold text-slate-900"
                >
                  Dashboard
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="text-slate-600"
                >
                  Monitor your automated Jira to GitHub workflow
                </motion.p>
                {statusMessage && (
                  <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mt-2 p-2 bg-blue-50 text-blue-800 text-sm rounded-lg border border-blue-200">
                    {statusMessage}
                  </motion.div>
                )}
              </div>
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="flex items-center gap-4"
              >
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleResetStats}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
                  disabled={!isConnected}
                >
                  Reset Stats
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleSystemControl}
                  className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-white transition-colors ${buttonConfig.color} disabled:opacity-50 disabled:cursor-not-allowed`}
                  disabled={!isConnected || buttonConfig.disabled}
                >
                  <ButtonIcon className={`w-5 h-5 ${buttonConfig.animate ? 'animate-spin' : ''}`} />
                  {buttonConfig.text}
                </motion.button>
              </motion.div>
            </div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { title: "Tasks Completed", value: metrics.tasksCompleted, changeType: "positive", icon: CheckCircle, color: "bg-green-600" },
                  { title: "Tasks Failed", value: metrics.tasksFailed, changeType: "negative", icon: XCircle, color: "bg-red-600" },
                  { title: "Tasks Pending", value: metrics.tasksPending, changeType: "positive", icon: Clock, color: "bg-orange-600" },
                  { title: "Tasks moved to HITL", value: metrics.tasksMovedToHITL, changeType: "negative", icon: Users, color: "bg-orange-600" }
                ].map((metric, index) => (
                  <motion.div
                    key={metric.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + index * 0.1, duration: 0.4 }}
                  >
                    <MetricCard {...metric} />
                  </motion.div>
                ))}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { title: "Pull Requests", value: metrics.totalPullRequests, changeType: "positive", icon: GitPullRequest, color: "bg-blue-600" },
                  { title: "PR Accepted", value: metrics.prAccepted, changeType: "positive", icon: GitMerge, color: "bg-green-600" },
                  { title: "Tokens Used", value: formatTokens(metrics.tokensUsed), changeType: "positive", icon: Zap, color: "bg-purple-600" },
                  { title: "Code Quality Scores", value: `${metrics.averageReviewScore}%`, changeType: "positive", icon: TrendingUp, color: "bg-blue-600" }
                ].map((metric, index) => (
                  <motion.div
                    key={metric.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 + index * 0.1, duration: 0.4 }}
                  >
                    <MetricCard {...metric} />
                  </motion.div>
                ))}
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-6"
            >
              <div className="lg:col-span-4">
                <WorkflowTracker currentIssue={currentIssue} workflowStage={workflowStage} />
              </div>
              <div className="lg:col-span-8">
                <ActivityLog logs={activityLogs || []} />
              </div>
            </motion.div>
          </motion.div>
        );
      case 'agents':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            <div>
              <motion.h1
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="text-2xl font-bold text-slate-900"
              >
                Agent Status
              </motion.h1>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-slate-600"
              >
                Monitor the health and activity of your backend agents
              </motion.p>
            </div>
            {/* Updated grid to force 4 columns */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {currentAgents
                .filter(agent => agent.id !== 'RebuilderAgent')
                .sort((a, b) => {
                  const order: Record<string, number> = {
                    'PlannerAgent': 1,
                    'AssemblerAgent': 2,
                    'DeveloperAgent': 3,
                    'ReviewerAgent': 4
                  };
                  return (order[a.name] || 99) - (order[b.name] || 99);
                })
                .map((agent, index) => (
                  <motion.div
                    key={agent.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 + index * 0.1, duration: 0.3 }}
                  >
                    <AgentCard agent={agent} />
                  </motion.div>
                ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="bg-white rounded-xl p-6 shadow-sm border border-slate-200"
            >
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Agent Health Summary</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="text-center"
                >
                  <div className="text-2xl font-bold text-green-600">4</div>
                  <div className="text-sm text-slate-600">Active Agents</div>
                </motion.div>
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="text-center"
                >
                  <div className="text-2xl font-bold text-red-600">0</div>
                  <div className="text-sm text-slate-600">Inactive Agents</div>
                </motion.div>
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="text-center"
                >
                  <div className="text-2xl font-bold text-slate-900">{currentAgents.reduce((sum, agent) => sum + (agent.id !== 'RebuilderAgent' ? agent.tasksProcessed : 0), 0)}</div>
                  <div className="text-sm text-slate-600">Total Tasks Processed</div>
                </motion.div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              className="bg-white rounded-xl p-6 shadow-sm border border-slate-200"
            >
              <h3 className="text-lg font-semibold text-slate-900 mb-6">Agent Performance</h3>
              {/* Updated grid to force 4 columns */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {currentAgents
                  .filter(agent => agent.id !== 'RebuilderAgent')
                  .sort((a, b) => {
                    const order: Record<string, number> = {
                      'PlannerAgent': 1,
                      'AssemblerAgent': 2,
                      'DeveloperAgent': 3,
                      'ReviewerAgent': 4
                    };
                    return (order[a.name] || 99) - (order[b.name] || 99);
                  })
                  .map((agent, index) => (
                    <motion.div
                      key={`performance-${agent.id}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 1.0 + index * 0.1 }}
                    >
                      <AgentPerformanceCard agent={agent} />
                    </motion.div>
                  ))}
              </div>
            </motion.div>
          </motion.div>
        );
      case 'metrics':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            <div>
              <motion.h1
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="text-2xl font-bold text-slate-900"
              >
                Performance Metrics
              </motion.h1>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-slate-600"
              >
                Analyze system performance and code quality trends
              </motion.p>
            </div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <PerformanceCharts data={performanceData} successRate={metrics.successRate} failureRate={100 - metrics.successRate} agents={agents} />
            </motion.div>
          </motion.div>
        );
      case 'settings':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            <SettingsPage />
          </motion.div>
        );
      default:
        return null;
    }
  };

  // If not authenticated, show password protection
  if (!isAuthenticated) {
    return <PasswordProtection onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex-1 p-8">
        <AnimatePresence mode="wait">
          <motion.div key={activeTab} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.3 }}>
            {renderMainContent()}
          </motion.div>
        </AnimatePresence>
      </div>
      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
}

export default App;
