// File: src/components/AgentPerformanceCharts.tsx
import React from 'react';
import {
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Agent } from '../types/dashboard';
import { motion } from 'framer-motion';

interface AgentPerformanceChartsProps {
  agents: Agent[];  // Now uses agents prop
}

export const AgentPerformanceCharts: React.FC<AgentPerformanceChartsProps> = ({ agents }) => {
  // Filter out RebuilderAgent
  const filteredAgents = agents.filter(agent => agent.name !== 'RebuilderAgent');

  // Prepare data for different chart types
  const agentTaskData = filteredAgents.map(agent => ({
    name: agent.name.replace('Agent', ''),
    tasks: agent.tasksProcessed,
    tokens: Math.round(agent.tokensConsumed / 1000), // Convert to K
    efficiency: Math.round((agent.tasksProcessed / (agent.tokensConsumed / 1000)) * 100) / 100
  }));

  const radarData = filteredAgents.map(agent => ({
    agent: agent.name.replace('Agent', ''),
    tasks: agent.tasksProcessed,
    tokens: Math.round(agent.tokensConsumed / 10000), // Scale down for radar
    efficiency: Math.round((agent.tasksProcessed / (agent.tokensConsumed / 1000)) * 10),
    successRate: agent.successRate || 0,
    uptime: agent.status === 'active' ? 100 : 0
  }));

  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444'];

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(1)}M`;
    } else if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Agent Efficiency Comparison */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Agent Efficiency (Tasks per 1K Tokens)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={agentTaskData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="efficiency"
              stroke="#10B981"
              strokeWidth={3}
              dot={{ fill: '#10B981', strokeWidth: 2, r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Agent Performance Radar */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Agent Performance Overview</h3>
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="agent" />
            <PolarRadiusAxis angle={90} domain={[0, 'dataMax']} />
            <Radar
              name="Tasks"
              dataKey="tasks"
              stroke="#3B82F6"
              fill="#3B82F6"
              fillOpacity={0.1}
              strokeWidth={2}
            />
            <Radar
              name="Efficiency"
              dataKey="efficiency"
              stroke="#10B981"
              fill="#10B981"
              fillOpacity={0.1}
              strokeWidth={2}
            />
            <Radar
              name="Success Rate"
              dataKey="successRate"
              stroke="#EF4444"
              fill="#EF4444"
              fillOpacity={0.1}
              strokeWidth={2}
            />
            <Tooltip />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};