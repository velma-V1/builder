// Phase 3A task submission: the only way a task enters the authoritative queue. Submits through
// the write-authorized orchestrator API (never the read-only snapshot API). Generates a
// client-side idempotency key that persists across a failed submission (so a retry is a true
// replay, not a new task) and rotates only after a confirmed successful submit.
import { useState, type FormEvent, type JSX } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { useSubmitTask } from "@/queries/useSubmitTask";

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

export function TaskSubmissionForm(): JSX.Element {
  const [projectRef, setProjectRef] = useState("");
  const [workstreamId, setWorkstreamId] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "high">("normal");
  const [modelPreference, setModelPreference] = useState("");
  const [expectedResult, setExpectedResult] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey);

  const submitTask = useSubmitTask();

  const canSubmit = projectRef.trim() !== "" && workstreamId.trim() !== "" && description.trim() !== "";

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!canSubmit) return;

    const trimmedModelPreference = modelPreference.trim();
    const trimmedExpectedResult = expectedResult.trim();

    submitTask.mutate(
      {
        project_ref: projectRef.trim(),
        workstream_id: workstreamId.trim(),
        description: description.trim(),
        priority,
        ...(trimmedModelPreference ? { model_preference: trimmedModelPreference } : {}),
        ...(trimmedExpectedResult ? { expected_result: trimmedExpectedResult } : {}),
        idempotency_key: idempotencyKey,
      },
      {
        onSuccess: () => {
          // Rotate the key only after a confirmed success, so a network failure leaves the
          // in-flight key intact for a true retry rather than minting a duplicate task.
          setDescription("");
          setModelPreference("");
          setExpectedResult("");
          setIdempotencyKey(newIdempotencyKey());
        },
      },
    );
  }

  return (
    <Card className="flex flex-col gap-sm">
      <h2 className="text-base font-semibold">Submit a task</h2>
      <form className="flex flex-col gap-sm" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-1 text-sm">
          Project / repo reference
          <Input
            value={projectRef}
            onChange={(event) => setProjectRef(event.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Workstream
          <Input
            value={workstreamId}
            onChange={(event) => setWorkstreamId(event.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Description
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Priority
          <Select
            value={priority}
            onChange={(event) => setPriority(event.target.value as "low" | "normal" | "high")}
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </Select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Model preference (optional)
          <Input
            value={modelPreference}
            onChange={(event) => setModelPreference(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Expected result (optional)
          <Textarea
            value={expectedResult}
            onChange={(event) => setExpectedResult(event.target.value)}
          />
        </label>
        <Button type="submit" disabled={!canSubmit || submitTask.isPending}>
          {submitTask.isPending ? "Submitting…" : "Submit task"}
        </Button>
        {submitTask.isError && (
          <p role="alert">{(submitTask.error as Error).message}</p>
        )}
        {submitTask.isSuccess && (
          <p role="status">
            {submitTask.data.created
              ? `Task ${submitTask.data.task_id} submitted.`
              : `Task ${submitTask.data.task_id} already existed for this idempotency key.`}
          </p>
        )}
      </form>
    </Card>
  );
}
