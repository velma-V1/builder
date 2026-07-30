# Roadmap PH-3 Exact Migration Manifest

All values are SHA-256 over exact checked-out bytes. Existing applied SQL content is unchanged.

| Ordered migration | SHA-256 |
|---|---|
| `migrations/audit/0001_audit_chain.sql` | `935e535a8db35693f94c6a30bcd9d312960eeeb24babea62e933ba7dfa06c433` |
| `migrations/runtime/0001_state.sql` | `2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c` |
| `migrations/runtime/0002_leases.sql` | `a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6` |
| `migrations/runtime/0003_memory.sql` | `65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587` |
| `migrations/security/0001_security_spine.sql` | `099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51` |
| `migrations/security/0002_permission.sql` | `a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb` |
| `migrations/security/0003_tools.sql` | `0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5` |
| `migrations/security/0004_watchdog.sql` | `21ad8fa85055e1e55b703a55865a442b4e1af907c39baf668f7fcf34a4488b80` |

`.gitattributes` enforces `*.sql text eol=lf`. The integrated verifier rejects a changed byte,
missing declared file, or undeclared SQL file in the audit/runtime/security migration roots.
A fresh local clone configured with `core.autocrlf=true` materialized LF-only bytes and reproduced
all eight hashes. Its committed 16-case portability suite passed, and the new Watchdog `0004` hash
and attribute assertions were independently verified; the final pushed M3 checkout runs all 18.
