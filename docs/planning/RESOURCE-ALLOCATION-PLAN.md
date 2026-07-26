# Resource Allocation Plan

**Document ID:** RES-ALLOC-000 · **Repository path:** `docs/planning/RESOURCE-ALLOCATION-PLAN.md`
**Status:** Active plan (subordinate to `01M §3.3/§3.6/§3.10`, `01J §3.3`, `docs/10A`) · **Owner:** Planning
(established RPH3 Pass 7; gap **G-02** resolved) · **Established:** 2026-07-26. **Governing inputs:** `01M`
(staged thresholds, emergency reserve), `01K §3.1` (per-execution resource controls), `01J §3.3` (executable
reservations), `docs/10A` (per-phase envelopes), `README` initial operating target.

Resource *allocation* here is the planning envelope + reservation policy; the **executable Resource
Scheduler** (CMP-RESSCHED) is **PH-4** and owns runtime admission/reservation. This plan records the
allocation targets and the Watchdog-monitored thresholds; it does not implement scheduling.

## 1. Target machine (planning envelope)

`README` initial operating target: Ryzen 7 7800X3D, RTX 4070 Super **12 GB VRAM**, **32 GB RAM**. All
per-phase envelopes below are planning expectations for one active lane; actuals are captured per phase in the
verification report environment table (`VERIFICATION-REPORT.template.md §1`).

## 2. Staged resource thresholds (`01M §3.3`, Watchdog-monitored)

```
NORMAL → WARNING → PAUSE → CRITICAL_CONTAINMENT   (+ REDUCED_MONITORING when a sensor is absent)
```

Thresholds use sustained-duration windows + separate recovery thresholds (hysteresis). Monitored signals:
CPU, RAM, GPU, VRAM, disk capacity, storage I/O, process count, thermal (where available). A missing sensor →
`REDUCED_MONITORING` (never a fabricated reading). The **emergency storage reserve** (`01M §3.10`) is protected
from ordinary tasks/caches/models/downloads; crossing the pre-reserve threshold pauses admission of new work.

## 3. Roadmap PH-3 (RPH3) allocation

RPH3 is pure enforcement over the frozen PH-2 SQLite runtime — **no models, no GPU, no network**.

| Component/task | CPU | RAM | VRAM | Storage | Notes |
|---|---|---|---|---|---|
| CMP-WATCH (T1) | low, bounded; independently restartable | small, bounded (`01M §3.1`) | none | small | own bounded allocation separate from Orchestrator |
| CMP-AUDITW/AUDITV (T4) | low | < 256 MB | none | append-only audit store (grows; retention-governed) | durable append |
| CMP-APPROVAL/PERM (T3/T2) | low | < 256 MB | none | security-spine store (small) | SQLite |
| CMP-TOOLREG/TOOLGW/FILEOP/DIAG (T5) | low (gateway); tool execution is resource-bounded per `01K §3.1` | < 512 MB | none | bounded file/archive limits | the gateway enforces per-execution caps; the sandbox itself is PH-5 |
| **RPH3 phase envelope** | — | **1–2 GB** | **none** | **< 100 MB** (+ audit store) | matches `docs/10A §3` PH-3 row |

**Per-execution controls (`01K §3.1`, enforced by CMP-TOOLGW at the seam):** wall-clock timeout, idle timeout,
CPU/RAM ceiling, writable-storage quota, process/thread count, created-file count, stdout/stderr/log size,
download/transfer limits, archive entry/depth/decompressed-size limits, complete process-tree tracking +
termination. A **limit increase is a permission change** (routes to CMP-PERM/CMP-APPROVAL).

## 4. Reservation policy (forward — PH-4 owns execution)

Reservations-before-use and `≤1 GPU-heavy on 12 GB` (`01D §2.13`, `01J §3.3`) bind at **PH-4** (CMP-RESSCHED)
when models run. RPH3 requires no reservation (no model/GPU). Recorded here so the PH-4 planning pass extends
this plan rather than forking it.

## 5. Per-phase envelope index (from `docs/10A §3`)

PH-1/PH-2 < 1 GB / no GPU · PH-3 (RPH3) 1–2 GB / no GPU · PH-4 up to 12 GB VRAM + ~16 GB RAM / ≤1 GPU-heavy ·
PH-5 2–4 GB / disposable sandboxes · PH-6 full envelope / 3 lanes · PH-7 2–6 GB · PH-8 2–4 GB. `docs/10A`
remains the authoritative per-phase execution map; this plan adds the reservation/threshold policy view.

## 6. Update rules

Regenerated when `01M` thresholds, `docs/10A` envelopes, or the target machine change, and extended (not
forked) by PH-4 when CMP-RESSCHED lands. Non-overriding of its governing sources; superseded by pointer.
