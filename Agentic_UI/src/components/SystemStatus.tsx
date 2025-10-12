import React from 'react';
import { CheckCircle, AlertCircle, WifiOff } from 'lucide-react';
import { motion } from 'framer-motion';

interface SystemStatusProps {
  isConnected: boolean;
  isSystemRunning: boolean;
  error?: string | null;
  agentsReady?: {
    task_agent: boolean;
    developer_agent: boolean;
    reviewer_agent: boolean;
    rebuilder_agent: boolean;
    jira_client: boolean;
  };
}

export const SystemStatus: React.FC<SystemStatusProps> = ({
  isConnected,
  isSystemRunning,
  error,
  agentsReady
}) => {
  const getConnectionStatus = () => {
    if (!isConnected) {
      return {
        icon: <WifiOff className="w-5 h-5 text-red-600" />,
        text: 'Disconnected',
        color: 'bg-red-50 border-red-200 text-red-800'
      };
    }

    if (isSystemRunning) {
      return {
        icon: <CheckCircle className="w-5 h-5 text-green-600" />,
        text: 'Connected & Running',
        color: 'bg-green-50 border-green-200 text-green-800'
      };
    }

    return {
      icon: <AlertCircle className="w-5 h-5 text-yellow-600" />,
      text: 'Connected (Idle)',
      color: 'bg-yellow-50 border-yellow-200 text-yellow-800'
    };
  };

  const status = getConnectionStatus();

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
      className={`rounded-lg p-4 border ${status.color} shadow-sm`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.div
            animate={{
              rotate: isSystemRunning ? [0, 360] : 0,
              scale: isSystemRunning ? [1, 1.1, 1] : 1
            }}
            transition={{
              duration: 2,
              repeat: isSystemRunning ? Infinity : 0,
              ease: "linear"
            }}
          >
            {status.icon}
          </motion.div>
          <div>
            <motion.h3
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="font-medium"
            >
              {status.text}
            </motion.h3>
            {error && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.75 }}
                className="text-sm mt-1"
              >
                {error}
              </motion.p>
            )}
          </div>
        </div>

        {agentsReady && isConnected && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Agents:</span>
            <div className="flex gap-1">
              {Object.entries(agentsReady).map(([agent, ready], index) => (
                <motion.div
                  key={agent}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.3 }}
                  className={`w-3 h-3 rounded-full ${
                    ready ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  title={`${agent}: ${ready ? 'Ready' : 'Not Ready'}`}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};
