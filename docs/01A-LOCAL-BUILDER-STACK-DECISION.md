# Approved Local Builder Stack Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

This decision explicitly supersedes any earlier requirement that Factory v1 support multiple local model runtimes from the beginning. It also supersedes any plan that treats Codex, VS Code, or another IDE as required for Factory operation.

## 1. Permanent local runtime

Ollama is the permanent local model runtime for Factory.

Factory v1 must install, configure, start, inspect, and use its local models through an Ollama runtime adapter. The control plane must not require a second local model runtime for normal operation.

Additional runtime adapters may be evaluated later, but they cannot become core dependencies or weaken Ollama compatibility without explicit approval.

## 2. Primary local coding worker

Aider connected to Ollama is the primary local coding worker for Factory v1.

Aider must operate as a bounded worker beneath the deterministic control plane. It receives task-scoped context, owned paths, permitted commands, model route, resource limits, and required evidence. It cannot independently grant permissions, change authoritative state, certify tests, declare completion, merge protected branches, publish, release, or bypass the sandbox.

The Aider integration must be replaceable behind a coding-worker interface so Factory architecture does not become inseparable from Aider internals.

## 3. Codex dependency removal

Codex is not a required Factory dependency.

Factory must be installable, runnable, maintainable, and capable of normal local development without a Codex subscription, Codex application, Codex CLI, Codex API, or Codex-specific workflow.

Codex may be used externally during development only as an optional aid. Its absence cannot disable any approved Factory v1 capability.

## 4. Primary interface

The Builder Dashboard is the primary Factory interface and normal development environment.

The Dashboard must provide the controls needed to inspect, edit, build, test, review, recover, and manage projects without opening an external IDE for normal work.

## 5. Built-in file explorer

Factory must include a project-aware file explorer that:

- displays the approved project tree;
- shows Git status, ownership, read-only, protected, generated, and disposable classifications;
- respects task contracts and permission boundaries;
- supports safe create, rename, move, and approval-gated deletion flows;
- exposes diffs, references, related tests, and change impact when available;
- cannot bypass the watchdog by directly modifying files.

## 6. Built-in Monaco editor

Factory must include an embedded Monaco code editor that supports normal source editing inside the Builder.

The editor must integrate with:

- the built-in file explorer;
- task ownership and permission status;
- unsaved-change and diff views;
- diagnostics and language-service adapters;
- search and replace;
- test and evidence views;
- checkpoint and rollback controls;
- the Aider local coding worker.

All writes still pass through controlled file operations. Monaco is an interface, not an authority boundary.

## 7. Normal development location

Normal Factory development must occur inside the Builder Dashboard.

External editors may be used for exceptional troubleshooting or user preference, but no approved workflow may require the user to work in an external IDE.

## 8. IDE adapter

Factory must include a disabled-by-default IDE adapter/plugin boundary.

The adapter may later support VS Code or another IDE through a narrow, permission-controlled protocol. Enabling it must be explicit and must not grant additional file, command, network, secret, or state authority beyond the active task contracts.

Factory core must never import, launch, depend on, or assume the presence of VS Code or any IDE.

## 9. VS Code status

VS Code is an optional external tool only.

It is not part of the required installation, primary workflow, control plane, evidence system, coding worker, or runtime. Failure or removal of VS Code cannot affect Factory operation.

## 10. OpenHands status

OpenHands is a possible future addition and is not part of Factory v1.

No v1 implementation, installer, test, acceptance criterion, or operating workflow may depend on OpenHands. A later evaluation must prove compatibility, value, isolation, resource use, and rollback before it can be proposed.

## 11. Hosted lanes

Existing approved hosted Worker–Reviewer lanes remain optional secondary capacity. They do not replace the Aider + Ollama primary local coding path and cannot be required for basic Factory operation.

## 12. Build-order effect

A minimum Builder workspace shell must be delivered early enough that later normal Factory development can occur inside it. The minimum shell includes:

- Dashboard application frame;
- built-in file explorer;
- Monaco editor;
- controlled terminal and task output;
- local Ollama connection status;
- Aider worker bridge;
- task, diff, test, approval, and checkpoint panels;
- disabled IDE-adapter configuration.

The complete monitoring, graphing, packaging, installation, and polished Dashboard experience remains part of the final dashboard section.

## 13. Acceptance rules

The decision is satisfied only when evidence proves that:

1. Factory starts and performs its core local workflow with Ollama and Aider while Codex, VS Code, and OpenHands are absent.
2. A user can browse and edit project files through the Dashboard.
3. Aider can perform a bounded coding task through Ollama under watchdog permissions.
4. Direct Dashboard, Monaco, Aider, or IDE-adapter operations cannot bypass ownership, deletion, approval, checkpoint, evidence, or rollback controls.
5. The IDE adapter is disabled by default.
6. Removing or disabling every external IDE leaves Factory functional.
7. Hosted providers being unavailable does not prevent the approved basic local workflow.