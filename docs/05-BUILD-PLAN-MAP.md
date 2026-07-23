# Factory Build Plan Map

**Status:** Approved planning order  
**Recorded:** July 23, 2026

## Planning rule

The Factory is a very large multi-system project. It will not be planned as one document.

Each section below receives its own locked specification and implementation plan. Each section is divided into approximately three to five independently testable tasks. No section advances until its acceptance criteria pass and its decisions are recorded.

Normal development must move into the Builder Dashboard as early as safely practical. A minimum workspace shell is therefore a required early milestone before later sections depend on external development tools.

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

## Early workspace milestone — minimum Builder shell

After Section 1 and before later normal development moves inside the Builder, implement the minimum primary-interface foundation.

Required outputs:

- launchable Builder Dashboard frame;
- built-in project file explorer;
- built-in Monaco code editor;
- controlled terminal and task output panel;
- safe file-operation boundary using Section 1 contracts;
- Ollama health and exact-model status;
- Aider coding-worker adapter connected to Ollama;
- task, diff, test, approval, checkpoint, and rollback panels;
- IDE adapter configuration present but disabled by default;
- proof that the shell works without Codex, VS Code, OpenHands, or hosted providers.

This milestone provides the working environment. Final Dashboard polish, complete graph views, installation, and packaging remain Section 8.

## Section 2 — Task queue and state machine

Define durable task states, transitions, dependencies, priority, serialization, cancellation, recovery, and restart behavior. Expose state through the minimum Builder shell as it is implemented.

Required outputs:

- state definitions;
- legal transition table;
- queue and dependency rules;
- persistent event record;
- idempotent restart behavior;
- state-machine tests;
- Dashboard task and queue status integration.

## Section 3 — Deterministic watchdog

Build the non-model authority that enforces contracts and state transitions.

Required outputs:

- permission enforcement;
- path and resource boundaries;
- heartbeat and stalled-task detection;
- retry and escalation control;
- recovery initiation;
- audit and evidence enforcement;
- controlled Dashboard, Monaco, file-explorer, terminal, and Aider command interfaces.

## Section 4 — Model and coding-tool routing and quotas

Connect the permanent local runtime, primary local coding worker, and approved optional hosted roster without granting models or workers system authority.

Required outputs:

- Ollama runtime adapter;
- Aider coding-worker adapter;
- approved-model and approved-worker registry;
- capability and availability checks;
- quota and usage ledger;
- local Worker, hosted Worker, Reviewer, takeover, and fallback routing;
- privacy and cloud-permission enforcement;
- no-silent-substitution tests;
- proof that basic operation remains local.

## Section 5 — Git, worktree, and sandbox isolation

Create repeatable and recoverable execution environments.

Required outputs:

- branch and worktree lifecycle;
- verified checkpoints;
- disposable Docker/WSL2 sandbox lifecycle;
- mount, network, secret, process, and resource policy;
- exact change tracking;
- safe Monaco and Aider write integration;
- sandbox destruction and rollback tests.

## Section 6 — Three Worker–Reviewer lanes

Activate three permanent parallel lane structures using the contracts, watchdog, router, Git, and sandbox layers. Hosted capacity remains optional; the local Aider + Ollama path remains primary.

Required outputs:

- lane lifecycle;
- local Aider worker packet and hosted Worker task packet;
- Reviewer packet with fresh context;
- `APPROVE`, `REVISE`, and `STOP` verdict handling;
- ownership-conflict prevention;
- three-component parallel demonstration;
- lane takeover and degraded-operation tests;
- proof that hosted lane loss does not disable local work.

## Section 7 — Testing, evidence, integration, and recovery

Prove that local and lane work can be independently verified, safely combined, and restored after failure.

Required outputs:

- evidence ledger;
- test-run records;
- completion gate;
- serialized integration coordinator;
- regression and failure-path execution;
- scope-drift recovery;
- repeated-failure limits;
- release-candidate verification packet;
- Dashboard evidence and recovery visibility.

## Section 8 — Complete Dashboard, packaging, and installation

Complete the primary Builder interface and package Factory for Windows 11 Home.

Required outputs:

- complete Dashboard and selectable panels;
- polished built-in file explorer;
- complete Monaco editing workflow;
- three-lane and local-worker activity views;
- approvals, tests, failures, checkpoints, rollback, model use, Aider activity, and hardware views;
- required graph views;
- optional IDE adapter/plugin, disabled by default;
- guided setup;
- installer or verified installation path;
- clean-machine installation test without Codex, VS Code, OpenHands, or hosted services;
- final documentation and release package.

## Self-hosting transition gates

The move from bootstrap tools into Factory happens in verified stages:

1. After safe file operations, the file explorer, and Monaco pass, normal browsing and editing move inside the Builder.
2. After the controlled terminal, command runner, test runner, and evidence capture pass, normal commands and testing move inside.
3. After the Ollama and Aider bridges pass, normal AI coding and repair move inside.
4. After Git, worktree, checkpoint, review, evidence, rollback, and recovery controls pass, normal repository management moves inside.
5. After complete local integration, security, restart, regression, and failure-path testing pass, Factory becomes the primary environment used to continue building and maintaining itself.

A workflow cannot move inside based on interface appearance alone. Its local replacement must pass deterministic acceptance tests first. After a successful cutover, the external workflow becomes an optional emergency or diagnostic fallback rather than a required dependency.

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
9. Do not add an external IDE, Codex, OpenHands, hosted provider, or alternate local runtime as a required dependency.
10. Move each development workflow into Factory immediately after its local replacement is verified; do not keep external tooling as the normal path without a documented blocker.

## Current next step

Execute the approved Section 1 implementation plan through the local-first build path, then implement the minimum Builder workspace shell and begin the staged self-hosting transition.