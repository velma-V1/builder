# Factory Build Plan Map

**Status:** Approved planning order  
**Recorded:** July 22, 2026

## Planning rule

The Factory is a very large multi-system project. It will not be planned as one document.

Each section below receives its own locked specification and implementation plan. Each section is divided into approximately three to five independently testable tasks. No section advances until its acceptance criteria pass and its decisions are recorded.

## Section 1 — Requirements and contracts

Define the authoritative schemas and rules every later subsystem consumes.

Required outputs:

- project intake contract;
- requirement record and traceability rules;
- task contract;
- path ownership contract;
- permission and approval contract;
- completion and evidence contract;
- change-control and scope-lock rules.

## Section 2 — Task queue and state machine

Define durable task states, transitions, dependencies, priority, serialization, cancellation, recovery, and restart behavior.

Required outputs:

- state definitions;
- legal transition table;
- queue and dependency rules;
- persistent event record;
- idempotent restart behavior;
- state-machine tests.

## Section 3 — Deterministic watchdog

Build the non-model authority that enforces contracts and state transitions.

Required outputs:

- permission enforcement;
- path and resource boundaries;
- heartbeat and stalled-task detection;
- retry and escalation control;
- recovery initiation;
- audit and evidence enforcement.

## Section 4 — Model routing and quotas

Connect the approved local and hosted roster without granting models system authority.

Required outputs:

- provider adapters;
- approved-model registry;
- capability and availability checks;
- quota and usage ledger;
- Worker, Reviewer, takeover, and local-fallback routing;
- privacy and cloud-permission enforcement;
- no-silent-substitution tests.

## Section 5 — Git, worktree, and sandbox isolation

Create repeatable and recoverable execution environments.

Required outputs:

- branch and worktree lifecycle;
- verified checkpoints;
- disposable Docker/WSL2 sandbox lifecycle;
- mount, network, secret, process, and resource policy;
- exact change tracking;
- sandbox destruction and rollback tests.

## Section 6 — Three Worker–Reviewer lanes

Activate three permanent parallel lanes using the contracts, watchdog, router, Git, and sandbox layers.

Required outputs:

- lane lifecycle;
- Worker task packet;
- Reviewer packet with fresh context;
- `APPROVE`, `REVISE`, and `STOP` verdict handling;
- ownership-conflict prevention;
- three-component parallel demonstration;
- lane takeover and degraded-operation tests.

## Section 7 — Testing, evidence, integration, and recovery

Prove that lane work can be independently verified, safely combined, and restored after failure.

Required outputs:

- evidence ledger;
- test-run records;
- completion gate;
- serialized integration coordinator;
- regression and failure-path execution;
- scope-drift recovery;
- repeated-failure limits;
- release-candidate verification packet.

## Section 8 — Dashboard, packaging, and installation

Expose the Factory clearly and package it for Windows 11 Home.

Required outputs:

- dashboard and selectable panels;
- three-lane activity view;
- approvals, tests, failures, checkpoints, rollback, model use, and hardware views;
- required graph views;
- guided setup;
- installer or verified installation path;
- clean-machine installation test;
- final documentation and release package.

## Drift-control rules

Every section must follow these rules:

1. Ask only decisions that materially change the section.
2. Ask one easy-to-understand question at a time.
3. Record each approved answer before relying on it.
4. Freeze scope before implementation.
5. Put new ideas into a later-review list unless required for current acceptance.
6. Give every task exact inputs, outputs, owned paths, forbidden paths, tests, and completion evidence.
7. Stop a drifting task, preserve evidence, return to the last safe point, correct the contract, and restart.
8. Do not claim completion without deterministic evidence.

## Current next step

Plan **Section 1 — Requirements and contracts** completely before writing implementation code.