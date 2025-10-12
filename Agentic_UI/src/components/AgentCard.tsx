// File: src/components/AgentCard.tsx
import React from 'react';
import { Clock, Lightbulb, Layers, Code, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface AgentCardProps {
  agent: {
    name: string;
    status: string;
    tasksProcessed: number;
    lastActivity: Date;
  };
}

export const AgentCard: React.FC<AgentCardProps> = ({ agent }) => {
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
        return <Clock className="w-5 h-5 text-slate-600" />;
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
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <motion.div
            whileHover={{ rotate: 360, scale: 1.1 }}
            transition={{ duration: 0.5 }}
            className="p-2 bg-slate-100 rounded-lg"
          >
            {getAgentIcon(agent.name)}
          </motion.div>
          <div>
            <motion.h3
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="font-semibold text-slate-900 text-base"
            >
              {agent.name.replace('Agent', '')}
            </motion.h3>
            <div className="flex items-center gap-1">
              <span className="text-sm text-slate-600 capitalize">{agent.status}</span>
            </div>
          </div>
        </div>
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [1, 0.8, 1]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            repeatType: "reverse"
          }}
          className={`w-3 h-3 rounded-full ${agent.status === 'active' ? 'bg-green-500' : 'bg-red-500'}`}
        />
      </div>

      <div className="space-y-3">
        <motion.div
          whileHover={{ x: 5 }}
          className="flex justify-between text-sm items-center"
        >
          <span className="text-slate-600">Tasks:</span>
          <span className="font-semibold text-slate-900">{agent.tasksProcessed}</span>
        </motion.div>
        <motion.div
          whileHover={{ x: 5 }}
          className="flex justify-between text-sm items-center"
        >
          <span className="text-slate-600">Last Activity:</span>
          <span className="font-semibold text-slate-900">
            {agent.lastActivity.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </motion.div>
      </div>
    </motion.div>
  );
};