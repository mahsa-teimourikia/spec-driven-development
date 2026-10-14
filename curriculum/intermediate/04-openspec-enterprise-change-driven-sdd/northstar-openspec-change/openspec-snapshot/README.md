# OpenSpec v1.14.1 snapshot

This manifest records the official release surface used to build Course 14. It pins the release tag to commit `87c3595ace6a2e22957f39ebe5b74c2f2316e0cb` and hashes the official schema and documentation inputs observed on 2026-10-12.

The snapshot is an upgrade and teaching control. It is not a copy of the OpenSpec implementation, vendor certification, security assessment, or production approval.

## Course mapping

| OpenSpec surface | Course use | Enterprise extension |
| --- | --- | --- |
| `openspec/specs/` | current agreed behavior | authoritative source/version binding |
| change proposal | intent and affected capabilities | scope and decision ownership |
| delta specs | explicit semantic change | baseline revision, authority, and concurrency validation |
| design | technical approach | ADR proposal routing |
| tasks | implementation checklist | bounded AWU enrichment |
| verify/validate | framework consistency checks | independent evidence and affected-invariant gates |
| sync/archive | spec evolution and historical preservation | exact-revision integration authorization and release separation |

Rebuild and review this snapshot before teaching against a newer OpenSpec release.
