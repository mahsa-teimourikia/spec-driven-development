# Enterprise Spec-Driven Development

> A 38-course learning program for designing an enterprise operating model in which coding agents can move quickly without receiving unlimited freedom.

## Start here

Open the **[deployed Learning Hub](https://mahsa-teimourikia.github.io/spec-driven-development/hub/)** and begin with [Course 01: Why agentic coding changes the PDLC](curriculum/beginner/01-why-agentic-coding-changes-pdlc/README.md). Continue through Course 07, then complete [Course 08: Non-functional requirements for agentic systems](curriculum/beginner/08-non-functional-requirements-agentic-systems/README.md) with its guided [notebook](curriculum/beginner/08-non-functional-requirements-agentic-systems/nfr_engineering.ipynb), deterministic [NFR lab](curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py), realistic [AI-2219 production-readiness workshop](curriculum/beginner/08-non-functional-requirements-agentic-systems/northstar-broker-nfrs/README.md), and the cumulative [deployed knowledge check](https://mahsa-teimourikia.github.io/spec-driven-development/quiz/).

This is not simply a tutorial for one specification framework. The central skill is turning organizational intent, architecture rules, product requirements, and engineering constraints into a hierarchy of durable specifications that agents can execute—and humans can govern.

## The learning journey

| Part | Courses | Focus |
| --- | ---: | --- |
| I · SDD foundations | 01–04 | Why the PDLC changes and how specifications form a hierarchy |
| II · Executable specifications | 05–10 | Requirements, scenarios, invariants, NFRs, ADRs, and traceability |
| III · SDD frameworks | 11–16 | Spec Kit, OpenSpec, Kiro, agent instructions, selection, and extensions |
| IV · Agentic PDLC | 17–23 | Delivery flows, brownfield work, parallel agents, reviews, and approvals |
| V · Enterprise controls | 24–31 | Security, AI governance, architecture, quality, compliance, and CI/CD |
| VI · Advanced agentic SDD | 32–38 | Context engineering, orchestration, drift, continuous specs, and evaluation |

The program ends with an **Enterprise Agent capstone**: design a real Agentic PDLC with authority boundaries, policy enforcement, evidence, exception handling, and measurable outcomes. See the [complete course plan](COURSE_PLAN.md).

## Course 01 outcome

Course 01 uses a fictional financial-services organization, Northstar Mutual, to show how the PDLC becomes a governed control loop. You will:

- distinguish prompts from durable specifications and observable evidence;
- triage a deficient Jira request, discover distributed context, and resolve applicability before precedence;
- compose organization, platform, domain, project, feature, and implementation rules with provenance;
- record ticket-versus-policy conflicts and author an executable change package before coding;
- run unsafe and governed candidate code in a temporary repository and contrast self-authored tests with independent gates;
- verify proposal-bound training approvals and generate separate merge and production-release evidence;
- choose direct change, lightweight specification, or full SDD in proportion to risk; and
- interpret current evidence about agentic coding without confusing speed with safe delivery.

## Course 02 outcome

Course 02 turns a mixed product ticket into an execution-ready, authority-aware artifact stack. You will:

- distinguish prompts, product intent, requirements, constraints, specifications, designs, ADRs, tasks, evidence, and agent instructions;
- replace “accurate” and an unqualified latency target with observable behavior and measurement context;
- verify hearsay against an authoritative domain-policy source;
- classify technology language by provenance so contracts and inherited constraints are preserved while ticket-level choices such as Redis remain design hypotheses;
- route local, architectural, policy, and exception decisions to the appropriate owners; and
- distinguish planned traceability from implemented, executed, passed, approved, and production-observed evidence.

## Course 03 outcome

Course 03 resolves distributed requirements into a bounded effective specification. You will:

- model organization, platform, domain, project, feature, and implementation layers without treating them as an automatic override ladder;
- evaluate applicability before precedence and retain evidence for applicable, non-applicable, and uncertain decisions;
- distinguish authority from specificity and confirm shared resource/scope before
  escalating a genuine conflict;
- reject superseded, stale, or provenance-incomplete sources without erasing their history;
- validate a scoped, conditional, expiring exception without rewriting the base
  requirement, enumerating every unaffected obligation, or mistaking fixture
  metadata for authenticated approval;
- compress the result into agent context that preserves IDs, source locators,
  applicability evidence, exception conditions, and stop states; and
- measure candidate-discovery precision and recall separately from applicability accuracy.

## Course 04 outcome

Course 04 turns requirement placement and federated ownership into an executable graph. You will:

- place enterprise, domain, project, and feature requirements according to decision rights rather than file proximity;
- distinguish requirement owners, consumers, implementation owners, and enforcement owners;
- select version-pinned policy sources through a project manifest instead of copying central policy;
- validate `SPECIALIZES`, `IMPLEMENTS`, and `EXCEPTS` relationships and reject silent weakening;
- distinguish documentation from detective and preventive enforcement;
- bind exceptions to a requirement version, scope, independent approver, and expiry;
- trace direct and transitive impact when `AI-030` changes; and
- compose bounded agent context while denying writes to policy and exception authorities.

## Course 05 outcome

Course 05 turns a sparse AI feature request into bounded, executable requirements. You will:

- distinguish unknowns, ambiguities, conflicts, design questions, and policy decisions;
- write source-backed requirements with stable identity, scope, owners, states, and evidence methods;
- let analysis and drafting proceed while an unresolved policy question keeps delivery disabled;
- validate typed RequirementGap states, evidence provenance, and exact draft correspondence around probabilistic generation;
- bind approval to exact content, current submission and requirement revisions, and broker authority;
- define fail-closed behavior, bounded retries, idempotency, and unknown-outcome reconciliation;
- detect stale agent context, semantic requirement changes, orphan tasks, and unimplemented requirements; and
- compare lexical and evidence-aware review rules on labelled cases without presenting the fixture as a benchmark.

## Course 06 outcome

Course 06 connects complementary requirement representations into one governed behavior. You will:

- keep user stories as intent while expressing obligations with explicit SHALL and EARS conventions;
- combine requirements, decision tables, scenarios, contracts, state machines, and invariants without creating competing sources of truth;
- distinguish schema validity from semantic validity, authorization, policy, approval, and execution;
- treat model-generated field, value, evidence, and status as proposals at a trust boundary;
- block stale, duplicate, out-of-order, ambiguous, and unsupported updates, and require an explicit reviewed resolution before replacing a verified conflicting value;
- prove frame conditions and prohibited transitions at a narrow mutation boundary;
- evaluate model extraction separately from trusted application decisions; and
- classify semantic requirement changes and trace direct and transitive impact.

## Course 07 outcome

Course 07 converts requirements into defensible, bounded evidence. You will:

- distinguish requirements, acceptance criteria, tests, evidence, and release decisions;
- design positive, negative, boundary, failure, stale-context, security, and compatibility criteria;
- pair reviewable examples with broad invariants, frame conditions, decision-table coverage, and state checks;
- use property-based reasoning and mutation testing without overclaiming proof;
- define AI evaluation populations, slices, label provenance, split controls, and explicit denominators;
- track evidence provenance, freshness, invalidation, independence, and limitations;
- separate measured quality from threshold ownership and release authority; and
- connect preventive controls with runtime signals that expose the applicable population.

## Course 08 outcome

Course 08 turns production qualities into governed measurement contracts. You will:

- replace vague adjectives with population-bound, measurable NFRs without inventing targets;
- define workload profiles, latency boundaries, percentiles, semantic good events, and capacity evidence;
- distinguish SLIs, internal SLOs, external SLAs, invariants, and error-budget response policies;
- design dependency-specific degradation that preserves work and reduces autonomy;
- bound provider attempts, tool calls, model turns, tokens, deadlines, and authoritative side effects;
- measure cost per successful compliant workflow rather than optimizing isolated API calls;
- specify least privilege, privacy-safe telemetry, trace completeness, and AI-quality slices; and
- keep production blocked when targets are unauthorized, capacity is unmeasured, or evidence is synthetic.

## Run locally

Everything in Courses 01–08 is credential-free and uses the Python standard library.

```bash
python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py
python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py --candidate all
python3 curriculum/beginner/02-from-prompt-to-executable-specification/lab.py
python3 curriculum/beginner/03-the-specification-hierarchy/lab.py
python3 curriculum/beginner/04-company-project-feature-requirements/lab.py
python3 curriculum/beginner/05-requirements-engineering-for-agents/lab.py
python3 curriculum/beginner/06-writing-executable-requirements/lab.py
python3 curriculum/beginner/07-acceptance-criteria-invariants-evidence/lab.py
python3 curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py
python3 -m unittest discover -s tests -v
python3 scripts/validate_course.py
```

To preview the Hub:

```bash
python3 -m http.server 8000
```

Then visit <http://localhost:8000/hub/>. Jupyter is optional; the repository validator executes the notebook top to bottom without requiring a notebook server.

## Operating principles

1. **Intent is hierarchical.** A feature specification inherits organization, platform, domain, and project constraints.
2. **Autonomy is bounded.** Agents receive explicit permissions, budgets, stop conditions, and escalation paths.
3. **Evidence closes the loop.** Tests, policy results, reviews, and production signals determine whether intent was satisfied.
4. **Controls are executable where practical.** Prose explains policy; schemas, tests, and CI gates enforce it.
5. **Ceremony is proportional.** Small, reversible changes do not need the same process as regulated, cross-repository work.
6. **Specifications evolve.** Drift must be detected and reconciled rather than hidden.

## Frameworks in the course

The program progressively uses [GitHub Spec Kit](https://github.github.com/spec-kit/), [OpenSpec](https://github.com/Fission-AI/OpenSpec), [Kiro Specs](https://kiro.dev/docs/specs/), `AGENTS.md`-style instructions, ADRs, policy-as-code, CI gates, evaluation, and multi-agent workflows. Frameworks are treated as implementation choices inside a broader operating model.

Learning with One+i · responsible AI, real-world impact. [oneplusi.io](https://oneplusi.io)
