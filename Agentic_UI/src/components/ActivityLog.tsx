import React from 'react';
import { Clock, Info, CheckCircle, AlertTriangle, XCircle, Trophy, Target, FileText } from 'lucide-react';
import { ActivityLog as ActivityLogType } from '../types/dashboard';
import { formatDistanceToNow } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

interface ActivityLogProps {
  logs: ActivityLogType[];
}

export const ActivityLog: React.FC<ActivityLogProps> = ({ logs }) => {
  // Safety check for logs
  if (!logs || !Array.isArray(logs)) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-slate-700" />
          <h3 className="text-lg font-semibold text-slate-900">Activity Log</h3>
        </div>
        <p className="text-sm text-slate-500">No activity logs available</p>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-600" />;
      case 'starting': return <Clock className="w-4 h-4 text-amber-500" />;
      default: return <Info className="w-4 h-4 text-blue-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'border-l-green-500 bg-green-50';
      case 'warning': return 'border-l-yellow-500 bg-yellow-50';
      case 'error': return 'border-l-red-500 bg-red-50';
      case 'starting': return 'border-l-amber-400 bg-amber-50';
      default: return 'border-l-blue-500 bg-blue-50';
    }
  };

  const getTotalScoreColor = (score: number) => {
    // Planner total score is now 0-100% scale (converted from 0-10)
    // 75% (7.5/10) = good, 60% (6/10) = acceptable, below 60% = needs improvement
    if (score >= 80) return 'text-green-600 bg-green-100 border-green-300';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100 border-yellow-300';
    return 'text-orange-600 bg-orange-100 border-orange-300';
  };

  const getPylintScoreColor = (score: number) => {
    // Pylint score is 0-10 scale
    if (score >= 8) return 'text-green-600 bg-green-100 border-green-300';
    if (score >= 6) return 'text-yellow-600 bg-yellow-100 border-yellow-300';
    if (score >= 4) return 'text-orange-600 bg-orange-100 border-orange-300';
    return 'text-red-600 bg-red-100 border-red-300';
  };

  const getReviewScoreColor = (score: number) => {
    // Review score is 0-100 scale
    if (score >= 80) return 'text-green-600 bg-green-100 border-green-300';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100 border-yellow-300';
    if (score >= 40) return 'text-orange-600 bg-orange-100 border-orange-300';
    return 'text-red-600 bg-red-100 border-red-300';
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 h-[500px] flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-5 h-5 text-slate-700" />
        <h3 className="text-lg font-semibold text-slate-900">Activity Log</h3>
      </div>

      <div className="space-y-3 flex-1 overflow-y-auto">
        {logs.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No activity yet</p>
        ) : (
          <AnimatePresence>
            {logs.map((log) => {
              // Safety checks for log object
              if (!log || !log.id) return null;

              const hasSubtasks = Array.isArray(log.subtasks) && log.subtasks.length > 0;
              const hasDocumentSections = Array.isArray(log.documentSections) && log.documentSections.length > 0;

              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3 }}
                  className={`border-l-4 p-3 rounded-r-lg ${getStatusColor(log.status || 'info')}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusIcon(log.status || 'info')}
                        <span className="font-medium text-slate-900">{log.agent || 'Unknown'}</span>
                        <span className="text-slate-600">•</span>
                        <span className="font-medium text-slate-900">{log.action || 'Activity'}</span>
                      </div>
                      <p className="text-sm text-slate-700 mb-1">{log.details || ''}</p>

                      {/* Display Overall Total Score prominently */}
                      {log.totalScore !== undefined && log.totalScore !== null && (
                        <div className="flex items-center gap-2 mt-2 mb-3">
                          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border-2 ${getTotalScoreColor(log.totalScore)}`}>
                            <Trophy className="w-5 h-5" />
                            <span className="text-sm font-bold">
                              Overall Score: {typeof log.totalScore === 'number' ? log.totalScore.toFixed(1) : log.totalScore}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Display Review Scores (Reviewer Agent) */}
                      {log.reviewScores && (
                        <div className="flex flex-wrap items-center gap-2 mt-2 mb-3">
                          {log.reviewScores.overall !== undefined && (
                            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${getReviewScoreColor(log.reviewScores.overall)}`}>
                              <Trophy className="w-4 h-4" />
                              <span className="text-xs font-bold">
                                Overall: {log.reviewScores.overall.toFixed(1)}%
                              </span>
                            </div>
                          )}
                          {log.reviewScores.completeness !== undefined && (
                            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${getReviewScoreColor(log.reviewScores.completeness)}`}>
                              <CheckCircle className="w-3.5 h-3.5" />
                              <span className="text-xs font-semibold">
                                Completeness: {log.reviewScores.completeness.toFixed(1)}%
                              </span>
                            </div>
                          )}
                          {log.reviewScores.security !== undefined && (
                            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${getReviewScoreColor(log.reviewScores.security)}`}>
                              <AlertTriangle className="w-3.5 h-3.5" />
                              <span className="text-xs font-semibold">
                                Security: {log.reviewScores.security.toFixed(1)}%
                              </span>
                            </div>
                          )}
                          {log.reviewScores.standards !== undefined && (
                            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${getReviewScoreColor(log.reviewScores.standards)}`}>
                              <Target className="w-3.5 h-3.5" />
                              <span className="text-xs font-semibold">
                                Standards: {log.reviewScores.standards.toFixed(1)}%
                              </span>
                            </div>
                          )}
                          {log.reviewScores.pylint !== undefined && (
                            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${getPylintScoreColor(log.reviewScores.pylint)}`}>
                              <FileText className="w-3.5 h-3.5" />
                              <span className="text-xs font-semibold">
                                Pylint: {log.reviewScores.pylint.toFixed(1)}/10
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Display standalone Pylint Score if available */}
                      {log.pylintScore !== undefined && log.pylintScore !== null && !log.reviewScores && (
                        <div className="flex items-center gap-2 mt-2 mb-3">
                          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border-2 ${getPylintScoreColor(log.pylintScore)}`}>
                            <FileText className="w-5 h-5" />
                            <span className="text-sm font-bold">
                              Pylint Score: {log.pylintScore.toFixed(1)}/10
                            </span>
                          </div>
                        </div>
                      )}

                      <div className="flex items-center gap-2 mt-2">
                        {log.issueId && (
                          <span className="inline-block bg-slate-200 text-slate-700 text-xs px-2 py-1 rounded font-medium">
                            {log.issueId}
                          </span>
                        )}
                        {hasSubtasks && (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600">
                            <Target className="w-3.5 h-3.5" />
                            {log.subtasks!.length} Subtask{log.subtasks!.length !== 1 ? 's' : ''}
                          </span>
                        )}
                        {hasDocumentSections && (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-purple-600">
                            <FileText className="w-3.5 h-3.5" />
                            {log.documentSections!.length} Section{log.documentSections!.length !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>

                      {/* Always show subtasks inline - no expand/collapse */}
                      {hasSubtasks && (
                        <div className="mt-3 pt-3 border-t border-slate-300">
                          <div className="space-y-2">
                            {log.subtasks!.map((subtask, index) => {
                              // Safety check for subtask
                              if (!subtask) return null;

                              const subtaskId = subtask.id !== undefined ? subtask.id : index;

                              return (
                                <div
                                  key={`${log.id}-subtask-${subtaskId}`}
                                  className="bg-white rounded-lg p-2.5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow"
                                >
                                  <div className="flex items-start gap-2">
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-bold text-slate-500">
                                          #{subtaskId}
                                        </span>
                                        {subtask.priority !== undefined && (
                                          <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-semibold">
                                            P{subtask.priority}
                                          </span>
                                        )}
                                      </div>
                                      <p className="text-xs text-slate-700 leading-relaxed font-medium">
                                        {subtask.description || 'No description'}
                                      </p>
                                      {subtask.reasoning && (
                                        <p className="text-xs text-slate-500 italic mt-1">
                                          {subtask.reasoning}
                                        </p>
                                      )}
                                    </div>
                                    {/* REMOVED: Individual subtask score display */}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Display document sections inline - no scores */}
                      {hasDocumentSections && (
                        <div className="mt-3 pt-3 border-t border-purple-300">
                          <div className="space-y-2">
                            {log.documentSections!.map((section, index) => {
                              // Safety check for section
                              if (!section) return null;

                              return (
                                <div
                                  key={`${log.id}-section-${index}`}
                                  className="bg-white rounded-lg p-2.5 border border-purple-200 shadow-sm hover:shadow-md transition-shadow"
                                >
                                  <div className="flex items-start gap-2">
                                    <FileText className="w-4 h-4 text-purple-600 mt-0.5 flex-shrink-0" />
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="text-sm font-bold text-purple-700">
                                          {section.title || 'Untitled Section'}
                                        </span>
                                      </div>
                                      <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
                                        {section.content || 'No content'}
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-slate-500 ml-3 flex-shrink-0">
                      {log.timestamp ? formatDistanceToNow(new Date(log.timestamp), { addSuffix: true }) : 'Just now'}
                    </span>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
};
