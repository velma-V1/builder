# WorldMonitor 07 — Installation Plan (dry-run; nothing applied)

Lifecycle phases (`build_lifecycle()`): inspect · prepare · install_later · start_later · health ·
stop_later · update_later · rollback_later · remove_later. Default is inspect/dry-run; a future
mutation requires an explicit `--apply`; **no** lifecycle mutation is implemented now.

Future isolation (declared, not applied): separate service/container, read-only rootfs, non-root, no
host networking, no Docker socket, bounded CPU/RAM, approved volumes only, dedicated network, egress
via broker only. Approved domains/ports come from the pinned manifest per deployment (empty until
the operator confirms).
