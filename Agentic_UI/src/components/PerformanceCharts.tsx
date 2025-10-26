// File: src/components/PerformanceCharts.tsx
import React from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { PerformanceData, Agent } from '../types/dashboard';
import { AgentPerformanceCharts } from './AgentPerformanceCharts';

interface PerformanceChartsProps {
  data: PerformanceData[];
  agents?: Agent[];
}

export const PerformanceCharts: React.FC<PerformanceChartsProps> = ({ data, agents = [] }) => {

  // UPDATED: Format date as "7-Oct" (day-three letter month, always two digits for day)
  const formatDate = (value: string) => {
    try {
      const date = new Date(value);
      const day = date.getDate().toString().padStart(2, '0');
      const month = new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date);
      return `${day}-${month}`;
    } catch {
      return value;
    }
  };

  const formatTokens = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  // UPDATED: Custom tooltip with proper date format
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 border border-slate-200 rounded-lg shadow-lg">
          <p className="font-semibold text-slate-900">{formatDate(label)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.dataKey === 'tokens' ?
                `${entry.name}: ${formatTokens(entry.value)}` :
                `${entry.name}: ${entry.value}${entry.dataKey.includes('Rate') || entry.dataKey.includes('Score') ? '%' : ''}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Agent colors - Added AssemblerAgent color
  const agentColors = {
    PlannerAgent: '#4CAF50',
    AssemblerAgent: '#2196F3',  // Blue for Assembler
    DeveloperAgent: '#808080',
    ReviewerAgent: '#FFC107'
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Task Performance Over Time */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Task Performance</h3>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 35 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              interval={0}
              tick={{ fontSize: 14 }}
              height={70}
              angle={0}
              textAnchor="middle"
            />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="tasks"
              stroke="#3B82F6"
              strokeWidth={2}
              name="Tasks Completed"
            />
            <Line
              type="monotone"
              dataKey="pullRequests"
              stroke="#10B981"
              strokeWidth={2}
              name="Pull Requests"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {/* Token Usage */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Token Usage</h3>
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 35 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              interval={0}
              tick={{ fontSize: 14 }}
              height={70}
              angle={0}
              textAnchor="middle"
            />
            <YAxis
              tickFormatter={formatTokens}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar dataKey="agent_activities.PlannerAgent.tokens_used" stackId="tokens" fill={agentColors.PlannerAgent} name="Planner" />
            <Bar dataKey="agent_activities.AssemblerAgent.tokens_used" stackId="tokens" fill={agentColors.AssemblerAgent} name="Assembler" />
            <Bar dataKey="agent_activities.DeveloperAgent.tokens_used" stackId="tokens" fill={agentColors.DeveloperAgent} name="Developer" />
            <Bar dataKey="agent_activities.ReviewerAgent.tokens_used" stackId="tokens" fill={agentColors.ReviewerAgent} name="Reviewer" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {/* Agent Efficiency chart (replace previous Agent Task Performance) */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        {/* AgentPerformanceCharts contains its own heading: "Agent Efficiency (Tasks per 1K Tokens)" */}
        <AgentPerformanceCharts agents={agents} />
      </div>
      {/* Code Quality Trend */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Code Quality Trend</h3>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 35 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              interval={0}
              tick={{ fontSize: 14 }}
              height={70}
              angle={0}
              textAnchor="middle"
            />
            <YAxis domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="sonarScore"
              stroke="#F59E0B"
              strokeWidth={3}
              dot={{ fill: '#F59E0B', strokeWidth: 2, r: 6 }}
              name="Quality Score"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};