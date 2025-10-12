import React, { useState } from 'react';
import { Clock, Info, CheckCircle, AlertTriangle, XCircle, ChevronDown, ChevronUp, ListChecks, Trophy } from 'lucide-react';
import { ActivityLog as ActivityLogType } from '../types/dashboard';
import { formatDistanceToNow } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

interface ActivityLogProps {
  logs: ActivityLogType[];
}

export const ActivityLog: React.FC<ActivityLogProps> = ({ logs }) => {
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-600" />;
      default: return <Info className="w-4 h-4 text-blue-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'border-l-green-500 bg-green-50';
      case 'warning': return 'border-l-yellow-500 bg-yellow-50';
      case 'error': return 'border-l-red-500 bg-red-50';
      default: return 'border-l-blue-500 bg-blue-50';
    }
  };

  const toggleExpand = (logId: string) => {
    setExpandedLogId(expandedLogId === logId ? null : logId);
  };

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-100';
    if (score >= 6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-5 h-5 text-slate-700" />
        <h3 className="text-lg font-semibold text-slate-900">Activity Log</h3>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        <AnimatePresence>
          {logs.map((log) => {
            const hasSubtasks = log.subtasks && log.subtasks.length > 0;
            const isExpanded = expandedLogId === log.id;

            return (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
                className={`border-l-4 p-3 rounded-r-lg ${getStatusColor(log.status)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusIcon(log.status)}
                      <span className="font-medium text-slate-900">{log.agent}</span>
                      <span className="text-slate-600">•</span>
                      <span className="font-medium text-slate-900">{log.action}</span>
                    </div>
                    <p className="text-sm text-slate-700 mb-1">{log.details}</p>

                    {/* Display total score and average score if available */}
                    {(log.totalScore !== undefined || log.averageScore !== undefined) && (
                      <div className="flex items-center gap-3 mt-2 mb-2">
                        {log.totalScore !== undefined && (
                          <div className="flex items-center gap-1">
                            <Trophy className="w-4 h-4 text-amber-600" />
                            <span className="text-xs font-semibold text-slate-700">
                              Total Score: <span className="text-amber-600">{log.totalScore}</span>
                            </span>
                          </div>
                        )}
                        {log.averageScore !== undefined && (
                          <div className="flex items-center gap-1">
                            <span className="text-xs font-semibold text-slate-700">
                              Avg: <span className={`px-2 py-0.5 rounded ${getScoreColor(log.averageScore)}`}>
                                {log.averageScore.toFixed(1)}
                              </span>
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-2 mt-2">
                      {log.issueId && (
                        <span className="inline-block bg-slate-200 text-slate-700 text-xs px-2 py-1 rounded">
                          {log.issueId}
                        </span>
                      )}

                      {/* Show expandable button if subtasks exist */}
                      {hasSubtasks && (
                        <button
                          onClick={() => toggleExpand(log.id)}
                          className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                        >
                          <ListChecks className="w-3.5 h-3.5" />
                          {log.subtasks!.length} Subtask{log.subtasks!.length !== 1 ? 's' : ''}
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </button>
                      )}
                    </div>

                    {/* Expandable subtasks section */}
                    <AnimatePresence>
                      {hasSubtasks && isExpanded && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.3 }}
                          className="mt-3 pt-3 border-t border-slate-300"
                        >
                          <div className="space-y-2">
                            {log.subtasks!.map((subtask) => (
                              <div
                                key={subtask.id}
                                className="bg-white rounded-lg p-2 border border-slate-200 shadow-sm"
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-xs font-bold text-slate-500">
                                        #{subtask.id}
                                      </span>
                                      {subtask.priority !== undefined && (
                                        <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                                          P{subtask.priority}
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-xs text-slate-700 leading-relaxed">
                                      {subtask.description}
                                    </p>
                                    {subtask.reasoning && (
                                      <p className="text-xs text-slate-500 italic mt-1">
                                        {subtask.reasoning}
                                      </p>
                                    )}
                                  </div>
                                  <div className={`flex-shrink-0 px-2 py-1 rounded font-bold text-sm ${getScoreColor(subtask.score)}`}>
                                    {subtask.score.toFixed(1)}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <span className="text-xs text-slate-500 ml-3 flex-shrink-0">
                    {formatDistanceToNow(log.timestamp, { addSuffix: true })}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
};
