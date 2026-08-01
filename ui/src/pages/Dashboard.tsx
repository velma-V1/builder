// The Builder Command Center page — one representative composition of the state boundaries:
// TanStack Query for the task snapshot, Zustand for presentation-only sidebar state, and (in a
// live build) the taskLifecycle XState machine driven by validated real-time events.
import type { JSX } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useSidebarStore } from "@/stores/sidebarStore";
import { useTaskSnapshot } from "@/queries/useTaskSnapshot";

export function Dashboard(): JSX.Element {
  const { collapsed, toggleCollapsed } = useSidebarStore();
  const { data: tasks, isLoading, isStale } = useTaskSnapshot("ws-1");

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className={collapsed ? "w-16" : "w-64"}>
        <Button variant="ghost" onClick={toggleCollapsed} aria-label="Toggle sidebar">
          {collapsed ? "»" : "«"}
        </Button>
      </aside>
      <main className="flex-1 p-lg">
        <Card>
          <h1 className="text-lg font-semibold">Builder Command Center</h1>
          {isLoading && <p>Loading task snapshot…</p>}
          {isStale && <p role="status">Snapshot may be stale — reconciling…</p>}
          <ul>
            {(tasks ?? []).map((task) => (
              <li key={task.task_id}>
                {task.task_id}: {task.state}
              </li>
            ))}
          </ul>
        </Card>
      </main>
    </div>
  );
}
