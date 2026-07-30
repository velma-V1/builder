# Approved Windows Activation Independence Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing requirement

Factory must function fully on Windows 11 Home regardless of whether Windows is activated.

Windows activation is not a development, testing, installation, operation, update, packaging, verification, release-candidate, or final-release requirement.

Activation status must not enable, disable, restrict, degrade, block, or alter any Factory capability, workflow, verification result, installer path, sandbox function, model operation, Dashboard function, recovery operation, update path, or release decision.

Windows activation remains entirely separate from Factory.

## 2. Explicit supersession

This decision explicitly supersedes every prior statement, assumption, recommendation, checklist item, acceptance criterion, or release gate that treated Windows activation as:

- a development prerequisite;
- an installation prerequisite;
- an operating prerequisite;
- a testing or verification prerequisite;
- a packaging prerequisite;
- a release prerequisite;
- a condition for full Factory functionality.

The approved host target remains Windows 11 Home. Windows 11 Pro, Hyper-V, and Windows Sandbox remain unnecessary. Approved isolation continues through Windows 11 Home-compatible components, including WSL2 and Docker Linux containers.

## 3. Implementation boundary

Factory must not:

- query activation status as an operational eligibility gate;
- block installation, startup, tasks, testing, updates, packaging, or release because Windows is unactivated;
- display activation warnings as Factory failures;
- depend on features available only through a specific activation state;
- claim that activation improves Factory safety, reliability, performance, or capability without separate verified evidence unrelated to licensing status.

Factory may report the Windows edition, version, build, required Windows features, driver state, virtualization capability, WSL2 state, Docker state, and hardware compatibility when relevant. Activation status is outside Factory's requirements and release authority.

## 4. Stage 12 correction

The Deployment, Updates, and Release stage must use the following corrected decisions:

- Windows 11 Home is the primary supported launch host.
- Factory supports both activated and unactivated Windows 11 Home equally.
- Development, testing, installation, operation, updating, packaging, verification, and release do not require activation.
- No activation check may block release approval.
- Activation is not included in Factory acceptance criteria.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. Factory installs and launches on unactivated Windows 11 Home;
2. all required Factory capabilities operate on unactivated Windows 11 Home;
3. all test, packaging, recovery, update, and release workflows complete without an activation dependency;
4. activation status is not used as a permission, capability, verification, or release gate;
5. activated and unactivated Windows 11 Home follow the same Factory behavior and support policy;
6. no required Factory component depends exclusively on Windows 11 Pro, Hyper-V, Windows Sandbox, or activation-gated behavior.