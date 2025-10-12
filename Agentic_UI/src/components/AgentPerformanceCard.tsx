// File: src/components/AgentPerformanceCard.tsx
import React from 'react';
import { Lightbulb, Layers, Code, CheckCircle } from 'lucide-react';
import { Agent } from '../types/dashboard';
import { motion } from 'framer-motion';

interface AgentPerformanceCardProps {
  agent: Agent;
}

export const AgentPerformanceCard: React.FC<AgentPerformanceCardProps> = ({ agent }) => {
  const formatTokens = (tokens: number) => {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(1)}M`;
    } else if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  // Get agent-specific icon
  const getAgentIcon = (agentName: string) => {
    switch (agentName) {
      case 'PlannerAgent':
        return <Lightbulb className="w-5 h-5 text-amber-600" />;
      case 'AssemblerAgent':
        return <Layers className="w-5 h-5 text-purple-600" />;
      case 'DeveloperAgent':
        return <Code className="w-5 h-5 text-blue-600" />;
      case 'ReviewerAgent':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      default:
        return <Code className="w-5 h-5 text-slate-600" />;
    }
  };

  return (
    <motion.div
      whileHover={{
        scale: 1.05,
        boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
        y: -5
      }}
      transition={{ duration: 0.2 }}
      className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 hover:border-blue-300 transition-all w-full h-[180px] flex flex-col justify-between cursor-pointer"
    >
      <div className="flex items-center gap-3 mb-4">
        <motion.div
          whileHover={{ rotate: 360, scale: 1.1 }}
          transition={{ duration: 0.5 }}
          className="p-2 bg-slate-100 rounded-lg"
        >
          {getAgentIcon(agent.name)}
        </motion.div>
        <h3 className="font-semibold text-slate-900 text-base">{agent.name.replace('Agent', '')}</h3>
      </div>

      <div className="space-y-3">
        <motion.div
          whileHover={{ x: 5 }}
          className="flex flex-col"
        >
          <span className="text-sm text-slate-600">Model:</span>
          <p className="font-semibold text-slate-900 text-sm truncate mt-1" title={agent.llmModel}>
            {agent.llmModel.split('/').pop()}
          </p>
        </motion.div>
        <motion.div
          whileHover={{ x: 5 }}
          className="flex justify-between text-sm items-center"
        >
          <span className="text-slate-600">Tokens:</span>
          <span className="font-semibold text-slate-900">{formatTokens(agent.tokensConsumed)}</span>
        </motion.div>
      </div>
    </motion.div>
  );
};