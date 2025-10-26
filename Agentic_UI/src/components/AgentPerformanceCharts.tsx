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
    // Return only the chart; parent component will provide the outer box and heading
    <>
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Agent Efficiency (Tasks per 1K Tokens)</h3>
      <ResponsiveContainer width="100%" height={380}>
        <LineChart data={agentTaskData} margin={{ top: 20, right: 30, left: 20, bottom: 35 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            interval={0}
            tick={{ fontSize: 14 }}
            height={70}
            angle={0}
            textAnchor="middle"
          />
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
    </>
  );
};