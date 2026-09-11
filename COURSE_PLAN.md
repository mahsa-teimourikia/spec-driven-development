# Course plan: Enterprise Spec-Driven Development for Agentic Software

## Governing vision

This program teaches an **enterprise operating model for agentic software development**, not simply how to use one SDD framework. Learners progressively turn organizational intent, architecture rules, product requirements, and engineering constraints into a hierarchy of durable specifications that coding agents can execute without unlimited freedom.

GitHub Spec Kit, OpenSpec, Kiro, Codex/Claude-style agent instructions, ADRs, policy-as-code, CI gates, evaluation, and multi-agent workflows appear as mechanisms inside that operating model. The program also teaches when a direct change or lightweight specification is more appropriate than full SDD.

The capstone is a designed, defended, and evaluated **enterprise Agentic PDLC**—not a toy application.

## Audience and prerequisites

The primary audience is senior software engineers, technical product managers, architects, platform engineers, quality/security practitioners, engineering managers, and transformation leaders. Learners should be comfortable with Git, pull requests, automated testing, and reading Python. Later courses assume API, CI/CD, security, and distributed-system fundamentals; the relevant concept is reviewed before use.

## Curriculum organization

The six conceptual parts are preserved below. Repository folders also expose learning levels for Hub filtering:

- **Beginner:** Courses 01–10, foundations and executable requirements.
- **Intermediate:** Courses 11–23, frameworks and end-to-end Agentic PDLC practices.
- **Advanced:** Courses 24–38, enterprise controls and advanced agentic SDD.
- **Enterprise Agent:** final operating-model capstone integrating the program.

Course numbers are global identifiers even though folders live under level directories.

## Evolving enterprise scenario

**Northstar Mutual** operates regulated insurance products and is building an Underwriter Assistant across several repositories. The scenario evolves from policy-document Q&A to shared APIs, identity, model gateways, evaluation, multi-agent changes, governance, compliance evidence, and production operations.

The scenario begins with these layers:

```text
Organization: privacy, approved clouds/models, IaC, production AI evidence
Platform:     AI gateway, OpenTelemetry, prompt registry, paved-road CI
Domain:       policyholder confidentiality, citations, human review
Project:      Underwriter Assistant architecture and conventions
Feature:      observable behavior for one change
```

Closely related courses preserve Northstar so learners can observe accumulated decisions and drift. By Course 20, learners inherit company policies, platform standards, project architecture, prior ADRs and specifications, known debt, existing CI, agent instructions, approved exceptions, and production telemetry. Shorter scenarios may be used when they reveal a technique more clearly.

### Practical environment progression

| Stage | Learner environment |
| --- | --- |
| Beginner | Deterministic primitives, structured requirements, traceability, and increasingly realistic repository fixtures |
| Intermediate | Real Git changes, framework artifacts, executable tests, agent instructions, and reviewable PR sequences |
| Advanced | Multiple repositories, policy-as-code, CI enforcement, architecture/security controls, orchestration, evaluation, and observability |
| Capstone | Product, platform, policy, infrastructure, and specification repositories governed as one Agentic PDLC |

Simulations remain useful for exposing internals, but they are not sufficient evidence of professional competence. The progression intentionally moves toward actual artifacts and delivery boundaries.

### Standard course design

Each future course follows this learning arc, adapted where the subject demands it:

1. why the problem exists and the enterprise scenario;
2. theory, mechanics, and failure patterns;
3. technology/framework choices and practical decision guidance;
4. Lab A for an isolated, observable primitive;
5. Lab B for a realistic repository or system artifact;
6. deliberate failure injection and mitigation;
7. evaluation, evidence limitations, and production design;
8. anti-patterns, exercises, checkpoint, and quiz coverage; and
9. for advanced work, operating-model ownership, metrics, and audit evidence.

## Outcomes by level

- **Beginner:** explain why agentic coding changes the PDLC; distinguish artifact types; compose specification layers; write behavioral, non-functional, and architectural decisions that can be traced to evidence.
- **Intermediate:** operate and compare SDD frameworks; design proportional greenfield, brownfield, bug, multi-repository, parallel-agent, PR, and approval workflows.
- **Advanced:** embed security, privacy, governance, quality, observability, compliance, supply-chain, and CI controls; engineer agent context, decomposition, compression, orchestration, drift detection, continuous specs, and evaluation.
- **Enterprise Agent capstone:** design roles, repositories, artifacts, workflows, controls, metrics, exceptions, and rollout for a real enterprise Agentic PDLC, then defend trade-offs with reproducible evidence.

## Part I — SDD foundations

| Course | Level folder | Topic | Status | Prerequisite | Learner evidence |
| --- | --- | --- | --- | --- | --- |
| 01 | beginner/01 | Why agentic coding changes the PDLC | **Available** | None | Control-plane simulation plus real repository change, applicability/provenance decisions, independent gates, evidence bundle |
| 02 | beginner/02 | Specs vs prompts vs requirements vs design | Planned | C01 | Artifact classification and repaired mixed artifact |
| 03 | beginner/03 | The specification hierarchy | Planned | C01–C02 | Precedence, provenance, freshness, and exception model |
| 04 | beginner/04 | Company vs project vs feature requirements | Planned | C03 | Requirement-location matrix, separate owner/RACI, applicability and enforcement map |

## Part II — Writing executable specifications

| Course | Level folder | Topic | Status | Prerequisite | Learner evidence |
| --- | --- | --- | --- | --- | --- |
| 05 | beginner/05 | Requirements engineering for agents | Planned | C01–C04 | Bounded change specification and ambiguity findings |
| 06 | beginner/06 | User stories, EARS, SHALL requirements, scenarios | Planned | C05 | Rewritten requirement set with positive/negative scenarios |
| 07 | beginner/07 | Acceptance criteria and invariants | Planned | C06 | Executable criteria, invariants, counterexamples |
| 08 | beginner/08 | Non-functional requirements | Planned | C06–C07 | Workload model, SLO-like criteria, measurement plan |
| 09 | beginner/09 | Architecture Decision Records | Planned | C02, C08 | ADR with alternatives, consequences, supersession rule |
| 10 | beginner/10 | Requirement traceability | Planned | C05–C09 | Bidirectional intent → design → task → code → evidence graph |

## Part III — SDD frameworks

| Course | Level folder | Topic | Status | Prerequisite | Learner evidence |
| --- | --- | --- | --- | --- | --- |
| 11 | intermediate/01 | GitHub Spec Kit | Planned | Part I–II | Constitution-to-convergence change plus flow-forward/living/flow-back persistence decision |
| 12 | intermediate/02 | OpenSpec | Planned | C10 | Brownfield case where spec says A, code/tests add B, and ticket requests C; current-truth/change-delta resolution |
| 13 | intermediate/03 | Kiro Specs | Planned | C06–C10 | Requirements/design/tasks flow plus defended routing of typo, export, API-contract, and AI-underwriting changes through direct, Quick Spec, Feature Spec, or specialist review |
| 14 | intermediate/04 | Agent instructions such as `AGENTS.md` | Planned | C03–C04 | Scoped cross-agent instructions and conflict tests |
| 15 | intermediate/05 | Comparing and choosing frameworks | Planned | C11–C14 | Weighted selection backed by scenario evidence |
| 16 | intermediate/06 | Custom enterprise extensions | Planned | C11–C15 | Organization-specific template/gate extension with upgrade path |

## Part IV — Agentic PDLC

| Course | Level folder | Topic | Status | Prerequisite | Learner evidence |
| --- | --- | --- | --- | --- | --- |
| 17 | intermediate/07 | Idea → discovery → spec → design → implementation | Planned | Parts I–III | End-to-end small-batch change and convergence record |
| 18 | intermediate/08 | Brownfield development | Planned | C12, C17 | Characterization baseline, change delta, migration checks |
| 19 | intermediate/09 | Bug fixes and small changes | Planned | C17–C18 | Proportional triage, minimal fix, regression evidence |
| 20 | intermediate/10 | Multi-repository development | Planned | C10, C17 | Cross-repo change graph and staged integration |
| 21 | intermediate/11 | Parallel agents | Planned | C17, C20 | Partitioned work, ownership leases, merge evidence |
| 22 | intermediate/12 | PR and review strategy | Planned | C17–C21 | Spec → design → implementation PR series compared with a mega-PR using latency, depth, rework, conflict, exception, and size evidence |
| 23 | intermediate/13 | Human approval gates | Planned | C04, C22 | Risk-tiered approvals, expiry, revocation, audit trail |

## Part V — Enterprise controls

| Course | Level folder | Topic | Status | Prerequisite | Learner evidence |
| --- | --- | --- | --- | --- | --- |
| 24 | advanced/01 | Security and privacy | Planned | C17–C23 | Threat model, least privilege, data/egress gates, abuse tests |
| 25 | advanced/02 | AI governance | Planned | C23–C24 | Model/use-case registry, evaluation and oversight policy |
| 26 | advanced/03 | Architecture governance | Planned | C09, C16–C23 | Automated standards plus exception and ADR workflow |
| 27 | advanced/04 | Testing and quality | Planned | C07–C08, C17 | Evidence portfolio, mutation/failure injection, release criteria |
| 28 | advanced/05 | Observability | Planned | C10, C27 | Delivery/runtime traces, redaction, correlation, SLOs |
| 29 | advanced/06 | Compliance | Planned | C23–C28 | Control-to-evidence mapping and reproducible audit bundle |
| 30 | advanced/07 | Supply-chain controls | Planned | C24, C27 | Provenance, dependency policy, attestations, release gate |
| 31 | advanced/08 | CI/CD enforcement | Planned | C24–C30 | Fail-closed policy pipeline, exceptions, rollback test |

## Part VI — Advanced agentic SDD

| Course | Level folder | Topic | Status | Prerequisite | Learner evidence |
| --- | --- | --- | --- | --- | --- |
| 32 | advanced/09 | Agent context engineering | Planned | C03–C04, C14, C31 | Context manifest, provenance, retrieval/evaluation harness |
| 33 | advanced/10 | Specification decomposition | Planned | C10, C20–C23, C32 | Work graph with contracts, owners, dependencies, stop rules |
| 34 | advanced/11 | Context compression | Planned | C32–C33 | Loss-aware compression and rare-control recall evaluation |
| 35 | advanced/12 | Multi-agent orchestration | Planned | C21, C33–C34 | Coordinator/worker protocol, budgets, idempotency, recovery |
| 36 | advanced/13 | Spec drift | Planned | C10, C28, C32–C35 | Drift detector, taxonomy, repair decision |
| 37 | advanced/14 | Continuous specification | Planned | C28, C31, C36 | Runtime feedback loop and governed spec evolution |
| 38 | advanced/15 | Specification-driven evaluation | Planned | C07–C10, C27, C32–C37 | Traceable eval dataset, independent judge design, release signal |

## Enterprise Agent capstone — Design the operating model

Learners design a real Agentic PDLC for an organization or realistic enterprise portfolio. The deliverable includes:

- operating principles, scope, non-goals, and risk tiers;
- specification repositories/layers, ownership, applicability, inheritance, and exceptions;
- framework and agent-instruction choices with portability/upgrade rationale;
- greenfield, brownfield, bug, small-change, multi-repo, and parallel-agent workflows;
- identity, permissions, sandboxes, budgets, approvals, retries, idempotency, rollback, and audit;
- requirements/design/task/code/evidence traceability;
- CI/CD, security, privacy, AI governance, architecture, compliance, supply-chain, and quality gates;
- delivery and runtime observability, drift, continuous specification, and evaluation;
- rollout stages, enablement, incentives, SLOs, adoption and outcome metrics; and
- a defended trade-off analysis showing where full SDD is intentionally not used.

## Technology choices and rationale

| Mechanism | Role | Selection rationale | Limitation taught explicitly |
| --- | --- | --- | --- |
| Markdown + Git | Durable portable artifacts | Diffable, reviewable, near code | Structure is not correctness or enforcement |
| Python standard library | Offline teaching primitives | Deterministic, credential-free, transparent | Not a production platform recommendation |
| GitHub Spec Kit | Extensible SDD process harness | Constitution, quality gates, cross-artifact analysis, convergence, broad integrations | Must be integrated with enterprise ownership/policy |
| OpenSpec | Current truth + change delta | Brownfield and cross-repository planning model | Stores are beta; operating controls remain external |
| Kiro Specs | Requirements/design/tasks variants | Requirements-first/design-first/quick/bug comparisons | Tool approval UX is not enterprise authorization |
| Agent instruction files | Standing local context | Cross-tool/repository proximity | Stochastic adherence and scope conflicts |
| ADRs | Consequential design decisions | Durable alternatives and consequences | Not complete behavioral specs |
| JSON Schema/OpenAPI | Typed data/interface contracts | Machine validation and ecosystem support | Partial view of business/system behavior |
| Policy-as-code and CI | Independent repeatable enforcement | Fail-fast gates and evidence | Only checks encoded policy and available inputs |
| Tests/evaluations/telemetry | Conformance and runtime signals | Observable feedback loop | Oracle, coverage, and attribution limitations |

## Evaluation approach

Every substantive course uses:

`Cases/data → run artifact and implementation → capture observable trace → compute measures → inspect failures → revise owning artifact → retest`

Measures evolve across the program: ambiguity findings, requirement coverage, source/provenance completeness, conflict detection, scenario/invariant coverage, NFR confidence, ADR decision quality, traceability completeness, cross-artifact consistency, policy-gate outcomes, review lead time, change batch size, permission violations, escaped defects, rollback rate, evidence quality, context recall, coordination conflicts, drift age, cost per accepted change, and runtime SLOs.

Notebook results must be generated by included code. Vendor benchmarks and research findings are contextual evidence, never substitutes for evaluation in the learner's organization.

## Diagram plan

- C01: inherited specification context and bounded Agentic PDLC feedback loop.
- C03–C04: hierarchy, applicability, ownership, and exception resolution.
- C10: traceability graph.
- C11–C16: framework artifact/lifecycle comparisons.
- C17–C23: PDLC state machine, work graph, parallel agents, review and approval boundaries.
- C24–C31: layered control/evidence pipeline.
- C32–C38: context supply chain, orchestration, compression loss, drift, continuous evaluation.
- Capstone: enterprise operating-model topology and rollout timeline.

Markdown uses editable Mermaid when appropriate. Notebook diagrams are accessible rendered SVG/PNG assets produced from validated coordinate specifications and inspected at intended size.

## Course 01 redesign record

The initial scaffold contained a narrower lesson, “From idea to verifiable specification.” It was audited before Course 01 development:

- **Retain:** deterministic offline execution, typed dataclasses, observable traces, failure injection, proportionality, notebook validation, Hub/quiz infrastructure, and FieldFlow examples for possible later requirements courses.
- **Deepen:** the prompt-versus-spec distinction, production boundaries, evaluation limits, and evidence concepts.
- **Consolidate:** course vision and roadmap into this plan; first-course navigation into one canonical lesson.
- **Replace:** FieldFlow reservation rules as Course 01's main scenario, because they teach feature contracts but not why agentic coding changes the enterprise PDLC.
- **Add:** Northstar Mutual scenario, six-layer control hierarchy, autonomy gradient, execution boundaries/budgets, conflict precedence, context ablation, current framework landscape, empirical delivery evidence, and enterprise operating-model progression.

The old lesson files are removed from the available curriculum rather than appended to or presented as a second Course 01. A second improvement audit retained Lab A and added:

- **Applicability before precedence:** applicable/not-applicable/uncertain decisions with fail-closed clarification.
- **Full provenance:** owner, source repository/path, version, commit, status, effective date, and exception authority.
- **Lab B:** a miniature Northstar repository with a terse ticket, distributed context, ADR, existing code/tests/infra, unsafe and governed candidate implementations, and temporary-workspace execution.
- **Independent evidence:** specification, policy, architecture, real unit-test, traceability, reviewer, and approval outputs in a release bundle, including explicit unverified risks.
- **Specification persistence:** change specification, living system truth, and decision-history distinctions tied to current Spec Kit and OpenSpec practice.

## Risk boundaries

- AI-generated specifications, reviews, policies, and evaluations are proposals unless an accountable owner approves them.
- Natural-language instructions do not replace authorization, sandboxing, egress controls, secrets management, policy enforcement, or independent review.
- Passing tests/evaluations establishes only what the selected evidence and oracle support.
- Formalized controls can be incomplete, stale, contradictory, or wrongly scoped; context selection itself must be evaluated.
- Multi-agent and retry workflows require bounded execution, idempotency, stop conditions, and recovery.
- Examples remain offline by default and never require production data or hidden credentials.

## Definition of done for a course

A topic becomes **Available** only when its chapter, primary notebook, reusable `lab.py`, focused checkpoint, Hub entry, and quiz questions form one coherent scenario and pass local validation. It must include a baseline, instrumentation, multiple meaningful experiments, failure injection and mitigation, evaluation with explicit limitations, production upgrade path, exercises, primary/official sources, and adjacent-course links.

Every intermediate and advanced course must also modify or evaluate a realistic software artifact—not only simulate the idea. Its learning package must connect theory, controlled implementation, repository work, failure behavior, and evidence. Beginner courses introduce this pattern progressively; Course 01 includes both a simulation and repository lab so learners see the destination from the start.
