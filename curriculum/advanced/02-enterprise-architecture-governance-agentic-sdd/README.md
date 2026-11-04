# Course 26 — Enterprise Architecture Governance for Agentic Spec-Driven Development

> Enterprise Spec-Driven Development · Part V: Enterprise Controls · Course 26 of 38

**Level:** Advanced / Staff Engineer, Enterprise Architect, Platform Engineer, and AI Technical Lead

**Estimated time:** 10–14 hours

**Prerequisites:** Courses 09, 16–17, and 20–25

**Case study:** Northstar Mutual — architecture governance for the AI Underwriting Assistant

**Practical stack:** Python, Git, JSON, ADRs, Rego concepts, AST analysis, dependency graphs, OpenAPI/JSON Schema concepts, and CI evidence

## Why this course matters

Course 25 established whether an AI use case, model, agent, and bounded authority may operate. It did not establish whether each implementation conforms to Northstar's enterprise architecture: model access through the enterprise gateway, capability-owned data, permitted dependency directions, approved technologies, or current architecture decisions.

Architecture guidance that lives only in diagrams, review meetings, or an architect's memory does not constrain an autonomous coding agent. The opposite failure is also costly: a rule set that prescribes every class and library destroys local design freedom and turns architecture into a central bottleneck.

The operating principle for this course is:

> Govern consequential boundaries and independently verify conformance; do not ask a coding agent to prove its own architecture compliance or predesign every implementation detail.

This course turns principles, standards, reference architectures, patterns, ADRs, constraints, and exceptions into a revision-bound control plane that produces actionable evidence without granting deployment authority.

The implementation is governed by an [OpenSpec-shaped change package](northstar-architecture-governance/openspec/changes/architecture-governance/proposal.md), a [report JSON Schema](northstar-architecture-governance/contracts/conformance-report.schema.json), an [OpenAPI capability boundary](northstar-architecture-governance/contracts/underwriting-data-api.openapi.yaml), and [requirement traceability](northstar-architecture-governance/traceability.json).

## Learning objectives

By the end, you should be able to:

1. Separate enterprise, solution, and implementation architecture decisions.
2. Build a hierarchy of principles, standards, reference architectures, patterns, ADRs, constraints, and exceptions.
3. Translate architecture intent into executable fitness functions and policy decisions.
4. Derive dependency, endpoint, technology, and Git facts from candidate repositories.
5. Distinguish static, dynamic, and evolutionary architecture evidence.
6. Govern ADR creation, supersession, conflict, scope, and traceability.
7. Design exact-scope, expiring exceptions with compensating-control evidence.
8. Detect layer violations, prohibited dependencies, cross-service cycles, and policy shadowing.
9. Bind conformance reports to an exact base, head, environment, policy revision, and observation producer.
10. Propagate architecture change through registered repositories, contracts, evaluations, and controls.

## Run the course

From the repository root:

```bash
python3 curriculum/advanced/02-enterprise-architecture-governance-agentic-sdd/northstar-architecture-governance/lab.py
python3 -m unittest tests.test_course_26 -v
```

Then open the guided [architecture-governance notebook](northstar-architecture-governance/architecture_governance.ipynb). The [lab guide](northstar-architecture-governance/README.md) explains the package, failure experiments, and staff workshop.

---

# Part I — Architecture governance as an operating model

## 1. Architecture is a system of decision rights

Architecture governance answers more than “is this design elegant?” It defines:

- which decisions are enterprise-wide because they protect shared risk or interoperability;
- which decisions belong to a solution because they concern one business capability;
- which implementation choices a team or agent may make locally;
- what evidence demonstrates conformance;
- who may approve an exception; and
- what must be reassessed when a decision changes.

A rule without an owner becomes advice. An owner without executable evidence becomes a review queue. Evidence without a current decision record becomes an orphaned check.

## 2. Three architecture scopes

| Scope | Typical decisions | Authority | Agent freedom |
|---|---|---|---|
| Enterprise | Identity, model gateway, data ownership, audit, approved platforms | Enterprise architecture and accountable domain owners | Conform or request governed exception |
| Solution | Service boundaries, contracts, workflow, reliability tactics | Solution architect and product engineering | Choose within enterprise constraints |
| Implementation | Modules, algorithms, internal data structures, refactoring | Delivery team | Broad freedom while fitness functions pass |

The scopes form an authority hierarchy, not a documentation hierarchy. A local ADR can refine an enterprise standard. It cannot silently repeal one.

## 3. The architecture artifact hierarchy

```text
principle
  └─ standard
      ├─ reference architecture
      ├─ approved pattern
      ├─ executable constraint / fitness function
      └─ architecture decision record
           └─ solution and implementation choices

exception → exact rule + resource + environment + subject digest + time window
```

Each artifact has a different job:

| Artifact | Purpose | Example |
|---|---|---|
| Principle | Durable direction and rationale | Capabilities own their data |
| Standard | Required or prohibited choice | AI inference uses the enterprise gateway |
| Reference architecture | Approved component and interaction model | AI service → gateway → model provider |
| Pattern | Reusable solution with context and tradeoffs | Transactional outbox for cross-service events |
| ADR | A scoped decision and its consequences | Adopt managed retrieval platform |
| Constraint | Machine-evaluable boundary | Domain code cannot import infrastructure |
| Exception | Temporary, bounded deviation | One development file, one digest, 30 days |

## 4. Architecture requirements are not prompts

“Follow the architecture” is not executable. A useful rule names scope, source of authority, prohibited or required condition, evidence, disposition, owner, and exception path:

```yaml
id: EA-001
scope: enterprise
statement: >
  AI services SHALL route model inference through the enterprise AI gateway.
applies_to: repositories tagged ai-enabled
evidence:
  - source dependency observation
  - endpoint observation
  - trusted runtime egress observation
failure_disposition: BLOCKED
owner: AI Platform Architecture
exception_authority: Enterprise Architecture Board
```

The agent sees a durable constraint. It still chooses internal module boundaries, algorithms, tests, and many dependencies.

---

# Part II — ADRs and durable architecture decisions

## 5. A useful ADR lifecycle

```text
PROPOSED → UNDER_REVIEW → ACCEPTED → SUPERSEDED
                   └────→ REJECTED
ACCEPTED → DEPRECATED → SUPERSEDED
```

An accepted ADR should remain historical evidence. When the decision changes, create a new record that supersedes the old record and retain the relationship. Editing an accepted record in place erases the rationale that governed earlier implementations.

The lab registry retains `ADR-027` as `SUPERSEDED` and points to `ADR-028`. A candidate that still cites `ADR-027` receives `REASSESSMENT_REQUIRED`, not silent success.

## 6. ADR authority and conflict

An ADR should record:

- stable identity and scope;
- status and accountable owners;
- context and forces;
- considered alternatives;
- decision and consequences;
- affected standards, systems, contracts, and evaluations;
- supersedes/superseded-by links; and
- required follow-up and review triggers.

An agent may draft the context, alternatives, and tradeoffs. It cannot accept its own enterprise decision. In the lab, a candidate-authored ADR proposing direct provider access conflicts with `EA-001`; it routes to architecture review and leaves the enterprise rule active.

## 7. ADRs are not enforcement mechanisms

An ADR captures intent and rationale. Fitness functions, network controls, schemas, policy engines, tests, and protected release gates enforce the decision. Treating an ADR file as a permission token creates a trivial bypass: the candidate could author the permission it needs.

---

# Part III — Architecture fitness functions

## 8. From review question to executable function

An architecture fitness function is an objective, repeatable check of an architectural characteristic. It should state:

1. the rule and scope;
2. the source facts;
3. the evaluation logic;
4. the success, uncertainty, and failure states;
5. the evidence producer;
6. the output and remediation; and
7. its known blind spots.

Northstar uses several kinds:

| Kind | Example | Evidence boundary |
|---|---|---|
| Static | AST import or dependency direction | Checked-out source at exact commit |
| Contract | OpenAPI/JSON Schema compatibility | Published and candidate contract revisions |
| Dynamic | Runtime egress only through gateway | Trusted network observation |
| Structural | No new service cycle | Registered dependency graph |
| Evolutionary | A changed ADR invalidates affected checks | Change-impact registry |

## 9. Do not collapse uncertainty into compliance

Static analysis can prove that a literal provider import exists. It may not determine a runtime destination assembled from configuration. The correct state is not “pass because we did not find it” and not always “permanent block.” It can be `INSUFFICIENT_EVIDENCE` with a request for trusted egress evidence.

The lab has six decision states:

| State | Meaning |
|---|---|
| `CONFORMANT` | Applicable checks pass for the exact revision |
| `CONFORMANT_WITH_EXCEPTION` | Every failing rule is covered by a valid exact-scope exception |
| `BLOCKED` | A known prohibited condition remains |
| `REVIEW_REQUIRED` | A legitimate architecture decision is needed |
| `INSUFFICIENT_EVIDENCE` | Required trusted facts are unresolved |
| `REASSESSMENT_REQUIRED` | A governing decision changed or became obsolete |

## 10. Actionable findings

An agent needs more than a red build. Each finding includes:

- stable rule ID and finding code;
- affected resource;
- disposition;
- source evidence such as file and line;
- human-readable reason; and
- accepted exception ID when applicable.

This enables remediation without granting the agent freedom to reinterpret the rule.

---

# Part IV — Deriving facts from repositories

## 11. Never trust `compliant: true`

The control plane must derive facts that matter to its decision. The Course 26 scanner:

- verifies the actual Git `HEAD`;
- proves the base is an ancestor;
- derives changed files from the commit range;
- parses Python imports and literal URLs with the AST;
- reads technology dependencies and service edges;
- calculates resource digests;
- resolves ADR status from an external registry; and
- signs the observation as a trusted producer.

Candidate labels, risk scores, expected outcomes, and self-issued exceptions are not decision inputs.

## 12. Static dependency checks

The fixture detects:

- direct model-provider SDKs;
- literal provider endpoints hidden behind generic HTTP clients;
- domain-to-infrastructure imports;
- private underwriting database clients;
- technologies that require an architecture decision;
- disallowed service edges; and
- cycles in the service graph.

Tools such as ArchUnit and dependency-cruiser provide analogous capabilities for supported ecosystems. The important enterprise design question is not which tool wins; it is how results bind to authority, revision, evidence, exception, and release decisions.

## 13. Cross-repository architecture

Repository-local checks cannot see every distributed-system property. A service can be clean internally while contributing to a cross-repository cycle or incompatible contract.

Maintain a system architecture registry containing stable repository and service identities, owned contracts, dependency direction and mode, relevant ADRs, and evidence revisions. Refresh it from trusted sources and compare the exact candidate change against the registered graph.

---

# Part V — Policy as code without policy theater

## 14. Separate policy decision from enforcement

The included [Rego policy](northstar-architecture-governance/policies/architecture.rego) illustrates declarative rules. The Python reference adds trust and lifecycle mechanics:

- authoritative policy and ADR registries;
- signed observation verification;
- typed decisions rather than one boolean;
- exact-subject exception validation;
- report binding to base, head, environment, and policy revision; and
- explicit evidence limitations.

Policy engines evaluate structured input. They do not make untrusted input authoritative. The enforcement point must obtain repository, identity, time, deployment, and network facts from appropriate trusted systems.

## 15. Policy revision is part of the subject

A green report under `EA-POLICY@6` cannot prove conformance under `EA-POLICY@7`. Reports therefore bind:

```text
repository + base commit + head commit + environment
+ policy revision + observation producer + generated time
```

Changing any material element requires reevaluation or explicit impact analysis.

## 16. Architecture evidence is not deployment authority

The report says what the trusted evaluator observed and how the active architecture policy classified it. It does not approve business risk, security risk, release timing, or production execution. Course 24's release controls and Course 25's AI-governance decision remain independent inputs.

---

# Part VI — Governed exceptions

## 17. Exception anatomy

An architecture exception needs:

- stable ID and accountable authority;
- exact rule and resource;
- environment;
- approved subject digest;
- issue and expiry time;
- status;
- rationale and risk owner;
- compensating controls with evidence; and
- remediation or retirement plan.

The lab calculates the subject digest from rule, resource, resource-content digest, environment, and policy revision. A development exception does not apply to production. Changing one byte of the approved resource invalidates the waiver.

## 18. Exceptions are not permanent standards

An exception must not become a hidden architecture branch. Track expiry, renewal frequency, age, affected risk, compensating-control health, and concentration by rule or team. Repeated exceptions may reveal a bad standard, missing platform capability, or weak enforcement. The right response can be to revise the standard—but only through its accountable lifecycle.

## 19. Negative exception tests

Course 26 proves that these do not waive a finding:

- expired record;
- wrong environment;
- wrong subject digest;
- revoked status;
- forged signature;
- absent compensating-control evidence; and
- not-yet-valid time window.

The control plane fails closed and reports why the exception was rejected.

---

# Part VII — Architecture change and drift

## 20. Drift has several forms

| Drift | Example | Detection |
|---|---|---|
| Implementation drift | Direct provider SDK appears | Source/dependency fitness function |
| Decision drift | Service still cites superseded ADR | ADR registry comparison |
| Policy drift | Report uses old policy revision | Revision binding |
| Runtime drift | Network destination bypasses gateway | Trusted egress observation |
| System drift | New cross-service cycle | Architecture graph comparison |
| Exception drift | Waiver expires while code remains | Time and status validation |

“The architecture document is current” proves none of these by itself.

## 21. Targeted invalidation

When Northstar replaces embedded retrieval stores with a managed platform, it should not blindly invalidate every enterprise system. The impact graph maps `ADR-028-RETRIEVAL-PLATFORM` to:

- affected repositories;
- versioned contracts;
- retrieval and residency evaluations; and
- architecture, data, and supply-chain controls.

This is continuous specification: governing decisions remain connected to the artifacts and evidence that depend on them.

## 22. Metrics that expose operating quality

Useful architecture-governance measures include:

- known-violation recall and clean-control false-positive rate;
- evidence completeness and stale-report rejection;
- exception validation accuracy, age, and recurrence;
- median time from finding to actionable remediation;
- proportion of standards with executable fitness functions;
- architecture decision lead time; and
- drift detected before versus after release.

The lab reports exact results only for deterministic training fixtures. Those figures are not a claim about production detection quality.

---

# Part VIII — Practical lab

## 23. Architecture

```text
candidate Git repository
          │
          ▼
trusted scanner derives base/head, imports, URLs,
technologies, dependencies, ADR refs, and digests
          │ signed observation
          ▼
authority + policy + ADR + system registries
          │
          ▼
fitness functions + exact exception validation
          │
          ▼
revision-bound conformance report
          │
          └── evidence for protected CI/release decision
```

The scenario descriptions contain expected labels for learners. The evaluator executes mutations in temporary Git repositories and never uses those labels to decide.

## 24. Failure experiments

| Mutation | Expected result |
|---|---|
| Direct provider SDK | `BLOCKED` |
| Provider endpoint via generic HTTP | `BLOCKED` |
| Generic HTTP with missing egress evidence | `INSUFFICIENT_EVIDENCE` |
| Domain imports infrastructure | `BLOCKED` |
| AI service accesses private database | `BLOCKED` |
| Unapproved vector database | `REVIEW_REQUIRED` |
| Exact valid development exception | `CONFORMANT_WITH_EXCEPTION` |
| Expired or wrong-environment exception | `BLOCKED` |
| Candidate modifies architecture policy | `BLOCKED` |
| Local ADR conflicts with enterprise standard | `REVIEW_REQUIRED` |
| Candidate cites superseded ADR | `REASSESSMENT_REQUIRED` |
| New service dependency cycle | `BLOCKED` |
| Report reused after HEAD advances | Reject as `REPORT_STALE_FOR_HEAD` |

## 25. Evidence produced

The reference run reports 13 golden scenarios, 16 independently executed adversarial cases, explicit numerator/denominator metrics, stale-report rejection, and targeted impact for the retrieval-platform decision. Tests additionally exercise forged observations and exceptions, wrong subjects, wrong environments, invalid time windows, and missing compensating-control evidence.

## 26. Production upgrades

Before production use, replace teaching HMAC keys and local registries with workload identity, managed signing and verification, rotation and revocation, protected policy-bundle distribution, real repository and artifact attestations, ecosystem-specific dependency tools, runtime network telemetry, contract registries, durable exception workflow, authoritative time, availability design, audit retention, and separation of duties.

Do not infer legal or regulatory compliance from an architecture report. Architecture governance must integrate with security, privacy, AI governance, compliance, and qualified organizational owners.

---

# Part IX — Staff-level design exercise

Northstar's Claims Assistant can summarize evidence but cannot decide a claim. A team proposes direct access to the claims database, a new vector platform, and autonomous writes to reduce latency.

Using the [starter architecture review](northstar-architecture-governance/workshop/starter/architecture-review.json), produce:

1. enterprise, solution, and implementation decision boundaries;
2. applicable principles, standards, reference patterns, and ADRs;
3. dependency, contract, data, runtime, and evolutionary fitness functions;
4. authoritative evidence producers and explicit blind spots;
5. a decision for the database and vector-platform proposals;
6. the smallest safe implementation freedom for the coding agent;
7. an exception model with compensating controls and expiry;
8. change-impact propagation across repositories and evidence; and
9. negative experiments demonstrating that the controls cannot be self-certified.

Compare your design with the [reference review](northstar-architecture-governance/workshop/reference/architecture-review.json) only after you can defend the decision rights and evidence boundaries.

## Checkpoint

A coding agent adds a file stating `architecture_compliant: true`, creates a local ADR approving direct provider access, and produces passing unit tests. Is the change architecture-conformant?

1. Yes, because the ADR and tests are repository evidence.
2. Yes, if the coding agent has an architect role in its prompt.
3. Only if trusted evaluators derive the applicable facts, resolve current enterprise authority, and produce a current decision for the exact revision; the local ADR cannot override the enterprise standard.

**Answer:** 3. Candidate artifacts can propose intent and provide test inputs. They do not establish authority or independently attest conformance.

## Completion criteria

You are complete when you can produce an architecture artifact hierarchy, current ADR registry, executable fitness-function set, independent observation contract, revision-bound report, governed exception design, cross-repository impact result, failure-injection evidence, metrics with limitations, and a clear list of decisions the agent is not authorized to make.

**Key takeaway:** Architecture governance becomes compatible with agentic delivery when enterprise intent is translated into durable, independently evaluated constraints at consequential boundaries—while teams retain freedom everywhere those boundaries do not require control.

## Authoritative references

- [AWS Prescriptive Guidance — Architectural decision records](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/)
- [Microsoft Azure Well-Architected Framework — Architecture decision records](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)
- [Microsoft Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/)
- [Open Policy Agent documentation](https://www.openpolicyagent.org/docs)
- [Open Policy Agent policy language](https://www.openpolicyagent.org/docs/policy-language)
- [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html)
- [dependency-cruiser rules reference](https://github.com/sverweij/dependency-cruiser/blob/main/doc/rules-reference.md)

Tool behavior and guidance should be rechecked against current official sources. The cited technology snapshot was reviewed on 2026-11-03.

Next: Course 27 — Testing and Quality for Agentic Systems.
