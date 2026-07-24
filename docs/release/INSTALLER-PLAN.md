# Installer Plan

**Status:** Authoritative planning record (L25.1) · **Phase:** PH-8
**Recorded:** July 24, 2026
**Governing:** `01O §2.2-13/§3.1-3.3`, `PD §23`, `01N`, `06 §10`. In force with `01R`.

## 1. Supported host & profile (`01O §3.2`)
Primary host: 64-bit **Windows 11 Home** — activated and unactivated receive **identical** support (`01N`). One versioned support profile records: minimum Windows build; minimum WSL version + Linux kernel; supported Docker Engine/Desktop versions; min/recommended RAM + storage; min CPU virtualization features; min GPU + VRAM (when GPU required); min GPU-driver + runtime; required reboots/features/host capabilities. Installer, release metadata, tests, and docs consume this profile rather than scattered constants.

## 2. Prerequisite classification (`01O §3.3`)
Each check is exactly one of `REQUIRED` (failure blocks install/capability), `RECOMMENDED` (visible warning + explicit override), `INFORMATIONAL` (recorded, non-blocking). A recommendation/informational result is never treated as a required failure without an approved support-profile change.

## 3. Activation independence (`01N`, `01O §3.1`)
Factory **never queries Windows activation** as an eligibility/capability/verification/release gate; never blocks install/startup/tasks/updates/packaging/release because Windows is unactivated; never displays activation warnings as Factory failures.

## 4. Prerequisite & runtime-artifact acquisition (`01O §2.4`, §3.4)
WSL2, Docker, Ollama, Python, GPU runtime components, and other external runtime artifacts: explicit operator approval before download; approved source + retrieval record; exact version + immutable digest/verified manifest; integrity verification before use; license/compatibility metadata; offline import where practical. No automatic BIOS/firmware modification (`01O §2.5`); actionable instructions when virtualization/prerequisite is unavailable (`01O §2.6`); minimal host modification (`01O §2.10`).

## 5. Storage & models
Separated storage domains (install files / persistent data / models / caches / logs / evidence / temp / project workspaces) with selectable locations; pre-install storage calculation (`01O §2.11-13`). Models are **excluded from the main installer** (`01O §2.14`); existing Ollama models detected to avoid duplication; missing models presented and downloaded only with explicit approval; model identity by immutable digest/verified manifest, not name/tag (`01O §2.15-17`).

## 6. Installer form (`01O §2.7-9`)
Guided installer first (exposes storage/prerequisite/model/permission/channel/data-location choices); repeatable setup script/process for development builds; a polished one-click installer is produced only after the core system stabilizes.

## 7. Offline distinction (`01O §4`)
Documentation distinguishes offline **runtime operation** (supported) from offline **initial installation** (not every prerequisite is offline-installable).

## 8. Gate G8 linkage
Installer evidence (unactivated install, REQUIRED/RECOMMENDED/INFORMATIONAL behavior, prerequisite acquisition, IP-5 clean-machine install) is required for the stable release verdict (`docs/release/RELEASE-PLAN.md §6`).
