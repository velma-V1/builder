import { useState, type JSX } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { usePhase3BActions, usePhase3BDetail } from "@/queries/usePhase3B";

export function Phase3BControls({ taskId, state }: { taskId: string; state: string }): JSX.Element {
  const { data, isLoading, isError } = usePhase3BDetail(taskId);
  const actions = usePhase3BActions(taskId);
  const [targetRef, setTargetRef] = useState("integration");
  const [rejectionReason, setRejectionReason] = useState("");
  if (isLoading) return <p>Loading verification evidence…</p>;
  if (isError || !data) return <p role="alert">Verification details unavailable.</p>;
  const pending = data.approval?.state === "PENDING" ? data.approval : null;
  const busy = actions.requestApproval.isPending || actions.approve.isPending || actions.reject.isPending;
  return (
    <section aria-label="Phase 3B verification and promotion">
      <h3>Verification</h3>
      {data.evidence ? (
        <>
          <p role="status">Result: {data.evidence.passed ? "PASS" : "FAIL"}</p>
          <ul>{data.evidence.items.map((item) => <li key={`${item.kind}-${item.detail}`}>{item.kind}: {item.passed ? "PASS" : "FAIL"} — {item.detail}</li>)}</ul>
        </>
      ) : <p>No durable verification evidence.</p>}
      <h3>Promotion manifest</h3>
      {data.manifest ? <ul>{data.manifest.files.map((file) => <li key={file.path}>{file.path} — {file.content_digest}</li>)}</ul> : <p>No promotion manifest.</p>}
      {state.toLowerCase() === "awaiting_approval" && !pending && (
        <>
          <Input aria-label="Promotion target" value={targetRef} onChange={(event) => setTargetRef(event.target.value)} />
          <Button disabled={busy || !data.evidence?.passed || !data.manifest} onClick={() => actions.requestApproval.mutate(targetRef)}>Request promotion approval</Button>
        </>
      )}
      {pending && (
        <>
          <p>Approval pending for {pending.target_ref}</p>
          <Button disabled={busy} onClick={() => actions.approve.mutate(pending.approval_id)}>Approve promotion</Button>
          <Input aria-label="Rejection reason" value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} />
          <Button variant="outline" disabled={busy || !rejectionReason.trim()} onClick={() => actions.reject.mutate({ approvalId: pending.approval_id, reason: rejectionReason })}>Reject promotion</Button>
        </>
      )}
      {(state.toLowerCase() === "promoting" || actions.approve.isPending) && <p role="status">Promotion in progress…</p>}
      {data.promotion && <p role="status">Promotion {data.promotion.outcome}: {data.promotion.reason}</p>}
    </section>
  );
}
