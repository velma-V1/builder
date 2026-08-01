// The Builder Command Center page — one representative composition of the state boundaries:
// TanStack Query for the task snapshot, Zustand for presentation-only sidebar state, and (in a
// live build) the taskLifecycle XState machine driven by validated real-time events.
//
// Phase 3A adds the operator-to-worker intake loop: a submission form, a cancel action for
// non-terminal tasks, a click-through details panel, and an orchestrator health badge. No
// approve/reject control exists here — that concept doesn't apply until a real worker produces
// results (Phase 3B/3C).
import { useState, type JSX } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useSidebarStore } from "@/stores/sidebarStore";
import { useTaskSnapshot, type TaskSnapshot } from "@/queries/useTaskSnapshot";
import { useCancelTask } from "@/queries/useCancelTask";
import { useTaskDetail } from "@/queries/useTaskDetail";
import { useOrchestratorHealth } from "@/queries/useOrchestratorHealth";
import { TaskSubmissionForm } from "@/components/TaskSubmissionForm";

// Mirrors the exact set of states with a legal edge to STOPPING in
// src/factory/orchestrator/state/transitions.py's ALLOWED_TRANSITIONS, plus QUEUED (which the
// backend's cancel path walks through a QUEUED->PLANNING pre-step first, its only legal edge).
// Deliberately not "non-terminal": FAILED is not one of the backend's TERMINAL_STATES (it can
// still move to ROLLED_BACK) but has no legal edge to STOPPING either, so it is not cancellable.
const CANCELLABLE_STATES = new Set([
  "queued",
  "planning",
  "running",
  "awaiting_approval",
  "verifying",
  "paused",
  "blocked",
  "quarantined",
]);

function isCancellable(state: string): boolean {
  return CANCELLABLE_STATES.has(state.toLowerCase());
}

function OrchestratorHealthBadge(): JSX.Element {
  const { data, isError } = useOrchestratorHealth();
  const reachable = !isError && data?.status === "ok";
  return (
    <span role="status" aria-label="Orchestrator health">
      Orchestrator: {reachable ? "healthy" : "unreachable"}
    </span>
  );
}

// A cancel mutation is scoped to a single row, not shared across the list -- calling
// useCancelTask() here (rather than once in Dashboard) gives each row its own independent
// isPending state, so cancelling one task never disables another task's Cancel button, and a
// row's own button disabling itself while its mutation is in flight prevents a second
// cancellation request for the same task before the first resolves.
function TaskRow({
  task,
  onSelect,
}: {
  task: TaskSnapshot;
  onSelect: (taskId: string) => void;
}): JSX.Element {
  const cancelTask = useCancelTask();
  return (
    <li>
      <button type="button" onClick={() => onSelect(task.task_id)}>
        {task.task_id}: {task.state}
      </button>
      {isCancellable(task.state) && (
        <Button
          variant="outline"
          size="sm"
          disabled={cancelTask.isPending}
          onClick={() => cancelTask.mutate({ taskId: task.task_id })}
        >
          Cancel
        </Button>
      )}
    </li>
  );
}

function TaskDetailsPanel({ taskId }: { taskId: string }): JSX.Element {
  const { data, isLoading } = useTaskDetail(taskId);
  if (isLoading) return <p>Loading task details…</p>;
  if (!data) return <p role="status">Task details unavailable.</p>;
  return (
    <dl>
      <dt>Task</dt>
      <dd>{data.task_id}</dd>
      <dt>State</dt>
      <dd>{data.state}</dd>
      <dt>Description</dt>
      <dd>{data.description}</dd>
    </dl>
  );
}

export function Dashboard(): JSX.Element {
  const { collapsed, toggleCollapsed } = useSidebarStore();
  const { data: tasks, isLoading, isStale } = useTaskSnapshot("ws-1");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className={collapsed ? "w-16" : "w-64"}>
        <Button variant="ghost" onClick={toggleCollapsed} aria-label="Toggle sidebar">
          {collapsed ? "»" : "«"}
        </Button>
      </aside>
      <main className="flex-1 p-lg flex flex-col gap-md">
        <Card>
          <h1 className="text-lg font-semibold">Builder Command Center</h1>
          <OrchestratorHealthBadge />
          {isLoading && <p>Loading task snapshot…</p>}
          {isStale && <p role="status">Snapshot may be stale — reconciling…</p>}
          <ul>
            {(tasks ?? []).map((task) => (
              <TaskRow key={task.task_id} task={task} onSelect={setSelectedTaskId} />
            ))}
          </ul>
        </Card>
        <TaskSubmissionForm />
        {selectedTaskId && (
          <Card>
            <h2 className="text-base font-semibold">Task details</h2>
            <TaskDetailsPanel taskId={selectedTaskId} />
          </Card>
        )}
      </main>
    </div>
  );
}
