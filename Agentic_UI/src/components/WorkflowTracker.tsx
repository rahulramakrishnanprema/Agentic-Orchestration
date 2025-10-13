// File: src/components/WorkflowTracker.tsx
import React from 'react';
import { Clock, CheckCircle } from 'lucide-react';

interface WorkflowTrackerProps {
  currentIssue: any | null;
  workflowStage: string;
}

const useWorkflowStatus = (pollInterval = 2000) => {
  const [currentAgent, setCurrentAgent] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/workflow_status');
        if (!res.ok) throw new Error('Fetch failed');
        const data = await res.json();
        if (isMounted) {
          setCurrentAgent(data.agent);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted) setError(err.message);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, pollInterval);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [pollInterval]);

  return { currentAgent, loading, error };
};

export const WorkflowTracker: React.FC<WorkflowTrackerProps> = ({ currentIssue }) => {
  const { currentAgent, loading, error } = useWorkflowStatus();

  if (loading) return <div>Loading workflow...</div>;
  if (error) return <div>Error: {error}</div>;

  const stages = [
    {
      name: 'Plan Fetching',
      agent: 'PlannerAgent'
    },
    {
      name: 'Document Assembly',  // NEW: Added Assembler stage
      agent: 'AssemblerAgent'
    },
    {
      name: 'Code Generation',
      agent: 'DeveloperAgent'
    },
    {
      name: 'Code Review',
      agent: 'ReviewerAgent'
    },
    {
      name: 'PR Creation',
      agent: 'TaskAgent'
    }
  ];

  // NEW: Determine if a stage is complete (previous stages when current is later)
  const currentIndex = stages.findIndex(stage => stage.agent === currentAgent);
  const isStageComplete = (index: number) => currentIndex > index;  // Mark previous as complete

  return (
    <div className="bg-white shadow sm:rounded-lg h-[500px] flex flex-col">
      <div className="px-4 py-5 sm:p-6 flex-1 flex flex-col">
        <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Workflow Status</h3>
        <div className="flex-1 overflow-y-auto space-y-4">
          {stages.map((stage, index) => {
            const isCurrent = currentAgent === stage.agent;
            const complete = isStageComplete(index);
            return (
              <div
                key={stage.agent}
                className={`p-4 rounded-lg ${isCurrent ? 'bg-blue-50' : 'bg-gray-50'}`}
              >
                <div className="flex items-center">
                  <div className="mr-3">
                    {complete ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <Clock className={`w-5 h-5 ${isCurrent ? 'text-blue-600 animate-spin' : 'text-gray-300'}`} />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">{stage.name}</div>
                    <div className="text-sm text-gray-500">{stage.agent}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};