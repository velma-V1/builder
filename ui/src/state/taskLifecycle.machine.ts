// XState v5 owns workflows and legal transitions — never authoritative truth. This machine's
// states/events/transitions are the exact contract described by
// factory.ui_studio.state_contracts.builder_command_center_workflow(); keep both in sync by hand
// until the compiler emits this file from that contract.
//
// This machine NEVER decides that a task actually completed/failed/was approved — it only
// reflects transitions the backend told it happened (via the real-time client). The backend
// (factory.orchestrator) remains the sole authoritative writer of task state.

import { setup, assign } from "xstate";

export type TaskLifecycleEvent =
  | { type: "start" }
  | { type: "finish" }
  | { type: "request_approval" }
  | { type: "approve" }
  | { type: "reject" }
  | { type: "fail"; reason?: string }
  | { type: "cancel"; reason?: string }
  | { type: "cancelled" };

interface TaskLifecycleContext {
  taskId: string;
  lastReason?: string;
}

interface TaskLifecycleInput {
  taskId: string;
}

export const taskLifecycleMachine = setup({
  types: {
    context: {} as TaskLifecycleContext,
    events: {} as TaskLifecycleEvent,
    input: {} as TaskLifecycleInput,
  },
}).createMachine({
  id: "task_lifecycle",
  context: ({ input }) => ({ taskId: input.taskId }),
  initial: "queued",
  states: {
    queued: {
      on: {
        start: "running",
        cancel: { target: "stopping", actions: assign({ lastReason: ({ event }) => event.reason }) },
      },
    },
    running: {
      on: {
        finish: "verifying",
        fail: { target: "failed", actions: assign({ lastReason: ({ event }) => event.reason }) },
        cancel: { target: "stopping", actions: assign({ lastReason: ({ event }) => event.reason }) },
      },
    },
    verifying: {
      on: {
        request_approval: "awaiting_approval",
        fail: { target: "failed", actions: assign({ lastReason: ({ event }) => event.reason }) },
        cancel: { target: "stopping", actions: assign({ lastReason: ({ event }) => event.reason }) },
      },
    },
    awaiting_approval: {
      on: {
        approve: "complete",
        reject: "failed",
        cancel: { target: "stopping", actions: assign({ lastReason: ({ event }) => event.reason }) },
      },
    },
    stopping: {
      on: { cancelled: "cancelled" },
    },
    complete: { type: "final" },
    failed: { type: "final" },
    cancelled: { type: "final" },
  },
});
