# Roadmap PH-3 Warning and Skip Register

## Tracked warning debt

| Item | Root cause | Repair | Verification | Status |
|---|---|---|---|---|
| SQLite `ResourceWarning` in approval failure-path coverage | two redundant one-shot `sqlite3.connect()` calls were never closed | removed the redundant leaked calls; retained the existing explicit connection/commit/close that creates the broken-store fixture | 309 focused RPH3 tests and 811 full-repository tests ran with `ResourceWarning` and Pytest unraisable warnings promoted to errors on Python 3.12/3.13/3.14 | RESOLVED |

No blanket warning filter or suppression was added. Accepted approval behavior is unchanged.

## Classified skip

| Test | Classification | Reason |
|---|---|---|
| `tests/contracts/security/test_path_attacks.py::test_symlink_escape_is_denied` | `NOT_TESTABLE` on this Windows host | creating the required symlink is unavailable under the current host privilege policy; the repository’s alternate path-authority escape coverage remains active |

No other skip is authorized or hidden.
