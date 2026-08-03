# WorldMonitor 07 — Managed Installation

Builder runs the pinned local Dockerfile build with `docker compose build --pull`; `compose pull`
is not treated as installation for this build-based service. The Dockerfile checks out the exact
commit and the final image carries the matching OCI revision label. Builder verifies the image ID
and revision before recording installation and again immediately before startup.

Startup waits for health with a bound. Failure triggers bounded `compose down --remove-orphans` and
records both the original failure and cleanup outcome. The service is non-root, read-only,
capability-dropped, resource-bounded, has no Docker socket, and uses an allowlisted egress sidecar.
Stop/disable/remove preserve named volumes; destructive volume deletion remains separately gated.
Actual execution is blocked here because Docker Desktop WSL2 integration is unavailable.
