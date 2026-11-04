# Architecture conformance delta specification

## ADDED requirements

### AG-REQ-001 — Revision-bound repository facts

The trusted scanner SHALL verify the actual Git `HEAD`, prove the base is an ancestor, and derive changed paths from the exact base/head range.

#### Scenario: caller names the wrong head

- **Given** a repository at revision B
- **When** the caller requests evaluation for revision A
- **Then** observation creation fails with `HEAD_BINDING_MISMATCH`

### AG-REQ-002 — Independently authenticated observation

The control plane SHALL accept architecture facts only from the registered observation producer with a valid signature.

#### Scenario: candidate forges observation results

- **Given** an observation with a modified signature
- **When** the control plane evaluates it
- **Then** evaluation fails with `OBSERVATION_AUTHENTICITY_UNVERIFIED`

### AG-REQ-003 — Current policy revision

The control plane SHALL evaluate only the active enterprise architecture policy revision.

### AG-REQ-004 — Governed model boundary

AI services SHALL use the enterprise AI gateway. Direct provider imports and endpoints SHALL produce blocking findings.

### AG-REQ-005 — Governed data boundary

AI services SHALL use the underwriting data API and SHALL NOT import private underwriting database clients.

### AG-REQ-006 — Layer dependency direction

Domain modules SHALL NOT depend on infrastructure modules.

### AG-REQ-007 — Service graph integrity

Candidate service edges SHALL match the approved graph, and the candidate graph SHALL remain acyclic.

### AG-REQ-008 — ADR authority and lifecycle

A local ADR that conflicts with an enterprise standard SHALL require accountable review. A reference to a superseded ADR SHALL require reassessment.

### AG-REQ-009 — Exact architecture exceptions

An exception SHALL have authenticated authority, approved status, exact rule, exact resource, matching environment, matching subject digest, valid time window, and compensating-control evidence.

### AG-REQ-010 — Evidence, not release authority

The report SHALL bind repository, base, head, environment, policy revision, producer evidence, findings, time, and limitations. It SHALL NOT authorize deployment.

### AG-REQ-011 — Targeted architecture impact

The control plane SHALL map a changed registered architecture decision to affected repositories, contracts, evaluations, and controls without invalidating unrelated systems.
