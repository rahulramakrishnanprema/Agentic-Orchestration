// File: src/components/AgentPerformanceCharts.tsx
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { Agent } from '../types/dashboard';

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
    </div>
  );
};