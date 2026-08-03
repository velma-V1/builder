import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type JSX } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cancelAgentZero, getAgentZeroOperation, getIntegrationLogs, getIntegrationStatuses, integrationAction, refreshWorldMonitor, runAgentZero } from "@/api/orchestrator";

const title = { "agent-zero": "Agent Zero", worldmonitor: "WorldMonitor" } as const;

export function IntegrationControls(): JSX.Element {
  const queryClient = useQueryClient();
  const statuses = useQuery({ queryKey: ["integrations"], queryFn: getIntegrationStatuses, refetchInterval: 5000 });
  const [instructions, setInstructions] = useState("");
  const [logs, setLogs] = useState<Record<string, string[]>>({});
  const lifecycle = useMutation({
    mutationFn: ({ name, action }: { name: "agent-zero" | "worldmonitor"; action: "install" | "start" | "stop" | "disable" | "remove" }) => integrationAction(name, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["integrations"] }),
  });
  const agent = useMutation({ mutationFn: runAgentZero });
  const world = useMutation({ mutationFn: refreshWorldMonitor });
  const recoveredAgent = statuses.data?.["agent-zero"]?.operation ?? null;
  const operationId = agent.data?.operation_id ?? recoveredAgent?.operation_id ?? null;
  const agentOperation = useQuery({
    queryKey: ["agent-zero-operation", operationId],
    queryFn: () => getAgentZeroOperation(operationId ?? ""),
    enabled: operationId !== null && (agent.data?.status ?? recoveredAgent?.status) === "RUNNING",
    refetchInterval: (query) => query.state.data?.status === "RUNNING" ? 1000 : false,
  });
  const effectiveAgent = agentOperation.data ?? agent.data ?? recoveredAgent;
  const effectiveWorld = world.data ?? statuses.data?.worldmonitor?.operation ?? null;
  const agentStatus = statuses.data?.["agent-zero"];
  const worldStatus = statuses.data?.worldmonitor;
  const agentEnabled = agentStatus?.configured_enabled ?? agentStatus?.state !== "DISABLED";
  const worldEnabled = worldStatus?.configured_enabled ?? worldStatus?.state !== "DISABLED";
  return <Card>
    <h2 className="text-base font-semibold">Managed integrations</h2>
    {(["agent-zero", "worldmonitor"] as const).map((name) => {
      const status = statuses.data?.[name];
      const disabled = !(status?.configured_enabled ?? status?.state !== "DISABLED");
      const action = status?.state === "READY" ? "stop" : "start";
      return <section key={name}>
        <h3>{title[name]}: {status?.state ?? "UNKNOWN"}</h3>
        <p>{status?.detail ?? "Status unavailable"}</p>
        {name === "worldmonitor" && status?.capability_coverage && <div role="status">
          <p>WorldMonitor capability scope: {status.capability_coverage.status}</p>
          <p>Implemented: {status.capability_coverage.implemented.join(", ")}</p>
        </div>}
        {!disabled && <><Button disabled={lifecycle.isPending} onClick={() => lifecycle.mutate({ name, action })}>
          {action === "start" ? "Start" : "Stop"} {title[name]}
        </Button>
        <Button variant="outline" onClick={() => lifecycle.mutate({ name, action: "install" })}>Install {title[name]}</Button>
        <Button variant="outline" onClick={() => lifecycle.mutate({ name, action: "disable" })}>Disable {title[name]}</Button>
        <Button variant="outline" onClick={() => lifecycle.mutate({ name, action: "remove" })}>Remove {title[name]} (preserve data)</Button>
        <Button variant="outline" onClick={() => void getIntegrationLogs(name).then((lines) => setLogs((current) => ({ ...current, [name]: lines })))}>View {title[name]} logs</Button>
        </>}
        {logs[name] && <pre aria-label={`${title[name]} logs`}>{logs[name].join("\n")}</pre>}
      </section>;
    })}
    {agentEnabled && <>
      <label htmlFor="agent-zero-instructions">Agent Zero instructions</label>
      <textarea id="agent-zero-instructions" value={instructions} onChange={(event) => setInstructions(event.target.value)} />
      <Button disabled={!instructions.trim() || agent.isPending} onClick={() => agent.mutate(instructions)}>Run Agent Zero task</Button>
      {effectiveAgent?.status === "RUNNING" && <p>Builder task is running and awaiting independent verification.</p>}
      {effectiveAgent?.status === "SUCCEEDED" && <p>Builder task {String(effectiveAgent.payload.task_id)} completed verification and promotion.</p>}
      {effectiveAgent?.reason && <p role="alert">{effectiveAgent.reason}</p>}
      {operationId && effectiveAgent?.status === "RUNNING" && <Button variant="outline" onClick={() => void cancelAgentZero(operationId)}>Cancel Agent Zero task</Button>}
    </>}
    {worldEnabled && <Button disabled={world.isPending} onClick={() => world.mutate()}>Refresh WorldMonitor</Button>}
    {effectiveWorld?.reason && <p role="alert">{effectiveWorld.reason}</p>}
    {Array.isArray(effectiveWorld?.payload.records) && <ul>{effectiveWorld.payload.records.map((item) => {
      const record = item as { id: string; summary: string; source: { name: string } };
      return <li key={record.id}><span>{record.summary}</span> — <span>{record.source.name}</span></li>;
    })}</ul>}
    {(lifecycle.error || agent.error || world.error) && <p role="alert">{String(lifecycle.error ?? agent.error ?? world.error)}</p>}
  </Card>;
}
