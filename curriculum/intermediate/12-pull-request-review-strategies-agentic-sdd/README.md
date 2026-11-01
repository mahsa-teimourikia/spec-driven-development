# Course 22 — Pull Request and Review Strategies for Agentic SDD

> Enterprise Spec-Driven Development · Part IV: Agentic PDLC · Course 22 of 38

**Level:** Advanced intermediate / staff AI scientist

**Prerequisites:** Courses 10 and 14–21

**Case study:** Northstar Mutual · AI-2500 Broker Document Review

**Practical stack:** Git, GitHub-style controls, GitHub Actions, OpenSpec, Python, protected acceptance tests, CODEOWNERS

## Course thesis

You should be able to explain, implement, evaluate, and productionize a pull-request review operating model that separates authorized intent, implementation quality, independent conformance evidence, and exact-revision integration compatibility without allowing an implementation agent to approve its own behavior.

## Why this course matters

Course 21 coordinated multiple coding agents across repositories. It established dependency-aware dispatch, leases, fencing, recovery, and an exact-revision integration barrier. The next constraint is human and organizational: agents can generate changes faster than people can understand and authorize them.

A Northstar delivery wave might produce 2,400 implementation lines, 1,100 test lines, four schemas, two migrations, specification edits, and architecture changes in hours. A single green pull request still leaves several questions:

- Is the intended behavior authorized?
- Is the design technically sound?
- Do tests measure the approved behavior rather than the implementation's assumptions?
- Are shared contracts compatible?
- Does the exact proposed merge state satisfy protected controls?
- Who is accountable for merge, deployment, and release?

The objective is not to maximize PR count or minimize time-to-approval. It is to choose review boundaries that let accountable people make distinct decisions with trustworthy evidence.

## Learning objectives

By the end, you should be able to:

1. Compare single, staged, stacked, and parallel-repository PR strategies.
2. Separate specification, architecture, implementation, conformance, integration, and release decisions.
3. Choose PR boundaries using semantic, authority, contract, data, test, reversibility, and expertise impact.
4. Prevent an agent from changing specifications, implementation, and test oracles to create self-confirming correctness.
5. Route review with CODEOWNERS-style ownership while preserving enterprise decision authority.
6. Bind approvals and trusted CI evidence to exact commits, specification digests, and contract digests.
7. Detect stale approval, unauthorized scope, self-approval, evidence mismatch, and combined-merge conflicts.
8. Use merge-group validation without confusing repository compatibility with cross-repository integration.
9. Compare lead time, review effort, rework, conflict discovery, escaped defects, and cost per verified change.
10. Build a credential-free Git-backed PR review control plane.

## Start here

Run the deterministic lab from the repository root:

```bash
python3 curriculum/intermediate/12-pull-request-review-strategies-agentic-sdd/northstar-pr-review/lab.py
```

Then use the guided [notebook](northstar-pr-review/pr_review_strategies.ipynb), inspect the [AI-2500 workshop](northstar-pr-review/README.md), and complete the six decisions in the [starter review package](northstar-pr-review/workshop/starter/review-package.json).

The lab uses only Python's standard library plus the installed Git executable. It creates temporary local repositories, never needs GitHub credentials, and grants no merge, deployment, or release authority.

---

## Part I — Why agentic coding changes review

### 1. Generation capacity is not delivery throughput

Parallel agents can increase review work-in-progress faster than review and integration capacity. A useful conceptual bound is:

\[
\text{verified throughput} \leq \min(\text{implementation capacity},\ \text{review capacity},\ \text{integration capacity})
\]

This is not a production estimator. Arrival variability, specialized ownership, rework, dependencies, and failure recovery also matter. It does expose one error: adding agents can lengthen lead time when downstream review is saturated.

### 2. Diff size is not decision complexity

One thousand generated client lines from an approved contract can be easy to validate. A five-line authorization bypass can require domain, security, and architecture review.

Assess at least:

| Dimension | Review question |
| --- | --- |
| Semantic scope | How many behaviors change? |
| Authority impact | Which protected decisions are affected? |
| Architecture impact | Does the change introduce dependencies or patterns? |
| Contract impact | Which producers and consumers can coexist? |
| Data impact | Are persistence, migration, or retention semantics changed? |
| Oracle impact | Can the contributor change expected outcomes? |
| Reversibility | Can the change be disabled or rolled back safely? |
| Expertise | Which accountable knowledge is required? |

Lines changed remain a diagnostic; they are not a sufficient governance policy.

### 3. One PR should represent a coherent review decision

A useful boundary is the smallest set of changes that can be meaningfully reviewed together. That does not mean one file, task, or agent per PR.

An API contract and its compatibility tests may form one decision. A contract change and unrelated UI styling usually do not. A database expand step, backfill, consumer migration, and contract step may require a sequence because the rollout properties differ.

---

## Part II — Four PR strategies

### 4. Single implementation PR

```text
approved intent → implementation + regression evidence → review → merge eligibility
```

Use it for bounded, independently verifiable changes with stable intent and architecture. `BUG-2415`, which corrects `> 80` to `>= 80` while leaving the approved threshold unchanged, does not normally need three governance PRs.

Main risk: a deceptively small diff can still alter protected behavior.

### 5. Spec-first staged PRs

```text
PR 1: intent and shared contracts
  ↓
PR 2: implementation and component evidence
  ↓
PR 3: integration and operational readiness
```

Use staged review when requirements, architecture, or shared contracts are real decision boundaries. Merging the first PR records a source-control transition; it does not replace the accountable approval mechanism that policy requires.

Main risk: unnecessary staging lengthens the critical path when no protected decision changed.

### 6. Stacked PRs

```text
contract → adapter → business behavior → integration
```

Each PR targets the preceding layer until the stack converges. Stacks can focus review, but an early change may invalidate every descendant's diff, approval, and evidence. Independently reviewable does not mean independently mergeable.

Main risk: rebases disguise subject changes unless review and evidence are rebound to the new head.

### 7. Parallel-repository PRs

```text
                         AI-2500
                            │
                  approved contract v2
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   AI Service PR      Review Service PR     UI PR
        └───────────────────┼───────────────────┘
                            ▼
                exact revision-set evidence
                            ▼
                   integration review
```

Stable shared interfaces can unlock concurrent repository work. Each PR must bind the same parent change and applicable contract revision. Local checks do not establish compatibility of the combined system revision set.

Main risk: fast local merges create cross-repository integration debt.

### 8. Strategy heuristic

| Change characteristic | Starting strategy |
| --- | --- |
| Localized, reversible fix | Single PR |
| New shared requirement or contract | Spec-first staged |
| Dependent implementation layers | Small stack |
| Stable contract and independent services | Parallel repository PRs |
| High-risk architecture decision | Independent architecture decision before implementation |
| Database evolution | Expand, migrate, contract sequence |
| Authorized emergency fix | Explicit emergency workflow with retrospective evidence |

Support several strategies under one evidence and authority model. Do not turn the heuristic into a universal law.

---

## Part III — Separate review dimensions

### 9. Intent

Are the requirements, exceptions, architecture choices, and contract changes authorized by their accountable owners?

### 10. Implementation

Is the design understandable, maintainable, secure, and consistent with repository architecture?

### 11. Conformance

Does executed behavior satisfy approved acceptance criteria and invariants, including negative and boundary cases?

### 12. Integration

Does this exact candidate work with the target branch and with the exact participating repository revisions?

A technically elegant classifier can violate a mandatory human-review rule. A conforming component can still break an older consumer. Preserving the dimensions prevents one green signal from impersonating all of them.

---

## Part IV — Ownership and repository controls

### 13. CODEOWNERS is routing, not enterprise authority

An illustrative repository file might contain:

```text
/.github/                 @northstar/repository-admins
/specifications/          @northstar/underwriting
/contracts/               @northstar/architecture
/src/authorization.py     @northstar/security
/src/classification/      @northstar/applied-ai
/database/migrations/     @northstar/data-platform
```

GitHub can request code-owner review and branch protection or rulesets can require it. The base branch's CODEOWNERS file governs the pull request, and protecting the ownership file itself is important. Still, a GitHub approval is not automatically an enterprise policy exception, model-risk approval, production deployment decision, or release authorization.

See GitHub's current [CODEOWNERS documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

### 14. Responsibility matrix

| Concern | Accountable owner |
| --- | --- |
| Business intent | Product or domain owner |
| Architecture | Architecture owner |
| Shared contract | Contract owner and affected consumers |
| Code quality | Engineering |
| Authorization and security | Security |
| AI evaluation | Applied AI / AI quality |
| Deployment readiness | Delivery / operations |

Not every change needs every owner. Trusted changed-path and impact analysis should resolve the applicable obligations.

### 15. Rulesets and branch protection are enforcement surfaces

Repository settings can require pull requests, current reviews, status checks, signed commits, linear history, or a merge queue. Configure them as defense in depth. The enterprise control plane must still know which semantic decisions were reviewed, which revision an approval covered, and whether cross-repository evidence remains current.

---

## Part V — The evidence envelope

### 16. Contributor metadata is a claim

PR descriptions, labels, agent reports, and declared changed paths help reviewers navigate. They are not authoritative facts.

| Information | Trust treatment |
| --- | --- |
| Title and description | Contributor-supplied claim |
| Changed paths | Derive from trusted Git base/head |
| Requirement references | Resolve against the approved registry |
| CI result | Verify producer, subject, check, and result |
| Approval | Verify identity, role, scope, subject, state, and expiry |
| Deployment approval | Resolve through the release authority separately |

### 17. Canonical review subject

The lab uses this logical envelope:

```yaml
pull_request: PR-AI-2500-03
change_id: AI-2500
work_unit: WU-AI
repository: ai-service
base_commit: <full-sha>
head_commit: <full-sha>
specification_digest: sha256:<digest>
contract_digest: sha256:<digest>
allowed_paths:
  - src/
  - tests/
required_scopes:
  - implementation
evidence:
  - EVID-PR-001
```

The envelope is an index, not proof. `allowed_paths` is a requested scope, not authority. The trusted service resolves the commits, checks ancestry, derives both sides of renames and deletions, loads the approved work unit, resolves versioned ownership by longest normalized prefix, verifies approval records, and validates evidence records.

### 18. Approval record

```yaml
approval_id: APR-IMPLEMENTATION-001
reviewer: <authenticated-principal>
role: engineering_reviewer
scope: implementation
resource: repository:ai-service
decision: approve_implementation
repository: ai-service
head_commit: <full-sha>
specification_digest: sha256:<digest>
contract_digest: sha256:<digest>
issued_at: <timestamp>
expires_at: <timestamp>
state: ACTIVE
```

Role text supplied by an agent is not authority. The protected registry binds the principal to an exact role, resource, and permitted decision. It also rejects approvals issued in the future, expired approvals, and approvals for another revision.

### 19. Evidence record

```yaml
evidence_id: EVID-PR-001
producer: protected-acceptance-runner
repository: ai-service
head_commit: <full-sha>
specification_digest: sha256:<digest>
contract_digest: sha256:<digest>
check_name: protected-acceptance
result: PASS
result_digest: sha256:<digest>
execution_id: RUN-<head-prefix>
protected_test_digest: sha256:<digest>
```

The digest is an integrity field, not authentication. The protected runner clones the exact commit from a trusted Git bundle, executes an independently controlled acceptance oracle, and writes the observed result into a registry that candidate records cannot populate. Production systems additionally need isolated execution, durable storage, attestable producer identity, tamper resistance, retention, and revocation semantics.

---

## Part VI — Prevent self-confirming review

### 20. Specification–implementation–test collusion

An agent changes:

```text
approved requirement → implementation → expected test result
```

Everything agrees and every test passes. Consistency is not correctness when the implementation author rewrote the authority and oracle.

For AI-2500, this change is unauthorized:

```text
before: ambiguous classifications require human review
after:  high-confidence ambiguous classifications may bypass review
```

### 21. Protect the acceptance oracle

The independent acceptance contract says:

```json
{
  "scenario": {"ambiguous": true, "confidence": 0.98},
  "expected": {"review_required": true},
  "authority": {"owner": "Underwriting Operations"},
  "revision": 2
}
```

An agent may propose additional cases. It cannot silently change this expected outcome. A protected CI job resolves the approved oracle rather than treating contributor tests as the only truth.

### 22. Independent execution boundary

```text
untrusted PR code and contributor tests
                  │
                  ▼
ephemeral least-privilege test environment
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
 protected acceptance    policy checks
        └─────────┬─────────┘
                  ▼
        exact-subject evidence
```

Running untrusted PR code is a security boundary. Avoid executing fork code in a privileged `pull_request_target` workflow. GitHub's current [secure `pull_request_target` guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target) recommends using `pull_request` when secret access is unnecessary and separating untrusted execution from privileged operations.

---

## Part VII — Freshness and invalidation

### 23. Approval is revision-sensitive

Approval at commit A does not automatically cover commit B. The policy may dismiss stale reviews, require approval of the latest reviewable push, or apply trusted impact analysis for a narrowly classified documentation change.

| Subject change | Required response |
| --- | --- |
| Implementation commit | Re-run checks and reassess review freshness |
| Requirement revision | Reassess intent and conformance |
| Contract revision | Recheck producers, consumers, and rollout |
| Security finding | Reassess security approval |
| Rebase onto changed target | Validate the new merge result |
| Model or prompt revision | Reassess AI behavior evidence |
| Proven documentation-only change | Apply trusted narrow impact analysis |

Exact-head binding is the reference default for consequential changes. A broader reuse policy needs explicit, testable impact rules.

### 24. Stale evidence is also unsafe

Evidence for `(spec S2, contract C2, commit A)` does not automatically apply to `(S2, C2, commit B)`. Schema stability does not imply behavioral stability. The Course 22 engine returns `EVIDENCE_SUBJECT_MISMATCH` when a check references the wrong head.

---

## Part VIII — Merge queues and integration

### 25. Individually green PRs can fail together

PR A and PR B may each pass against `main` yet conflict with one another. The lab creates two real Git branches that independently commit parser changes and then proves their combined merge conflicts.

### 26. Repository merge-group verification

GitHub merge queues test a proposed merged state against the latest target branch and earlier queued changes. GitHub Actions workflows that provide required checks for a merge queue need the separate `merge_group` trigger:

```yaml
on:
  pull_request:
  merge_group:

permissions:
  contents: read
```

See GitHub's current [merge queue documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

### 27. Cross-repository integration remains separate

A repository merge queue cannot make five repositories atomic. The system integration manifest must identify the exact candidate set:

```yaml
change_id: AI-2500
revisions:
  ai-service: <sha-a>
  review-service: <sha-b>
  underwriter-ui: <sha-c>
contract_digest: sha256:<digest>
integration_evidence_id: INT-2500-017
state: READY_FOR_INTEGRATION_REVIEW
```

If any component advances, the subject changes. Re-execute system checks or use an explicit trusted applicability analysis.

---

## Part IX — Review flow and metrics

### 28. Limit review work in progress

Illustrative policy:

```yaml
review_flow:
  max_open_implementation_prs_per_team: 4
  max_concurrent_architecture_reviews: 2
  dispatch_requires_available_review_capacity: true
```

These are teaching values, not recommendations. Calibrate limits using arrival rate, queue time, active review time, expertise, rework, and business priority.

### 29. Measure speed and effectiveness

| Metric | Definition |
| --- | --- |
| Review queue time | Ready-to-review until review begins |
| Active review time | Time spent examining the change |
| Review cycle time | Review request through final decision |
| Approval invalidation | Reviews made stale by later changes |
| Rework rate | Changes requiring another implementation cycle |
| Requirement defect detection | Unauthorized or incorrect behavior caught pre-merge |
| Contract conflict detection | Combined incompatibility caught pre-merge |
| Escaped defects | Problems discovered after integration or release |
| Cost per verified change | Engineering, model, CI, review, and rework cost per compliant outcome |

Comment count, approval count, and time spent are weak review-depth proxies. Controlled seeded-defect evaluations provide stronger evidence.

### 30. Event-based synthetic strategy comparison

The lab executes the same dependency graph and review-capacity assumptions for each strategy. Each result includes build start, review start, completion, review cycles, rework, and conflicts:

| Metric | Mega-PR | Staged | Parallel |
| --- | ---: | ---: | ---: |
| Lead time (hours) | 30 | 26 | 21 |
| Review effort (hours) | 11 | 8 | 9 |
| Rework (hours) | 9 | 3 | 4 |
| Late contract conflicts | 3 | 0 | 1 |

These values are computed by a deterministic event simulation, not supplied benchmark claims. They demonstrate why lead time alone cannot select a strategy, and conclusions remain bounded to the fixture's durations, dependencies, reviewer lanes, and rework assumptions.

---

## Part X — Practical lab

### 31. Architecture

```text
real temporary Git repositories
             │
             ▼
       trusted Git observer
       base, head, ancestry,
       rename-aware changed paths
             │
             ▼
     protected review resolver
   work-unit scope + ownership
             │
      ┌──────┴───────┐
      ▼              ▼
approval registry  protected CI registry
      └──────┬───────┘
             ▼
 ELIGIBLE_FOR_MERGE_REVIEW | BLOCKED
             │
             ▼
 merge/deploy/release remain separate
```

### 32. Executable experiments

| Experiment | Expected finding |
| --- | --- |
| Agent changes protected requirement | `UNAUTHORIZED_SPEC_CHANGE` |
| Shared contract lacks owner approval | `CONTRACT_APPROVAL_MISSING` |
| Approval binds an earlier commit | `STALE_REVIEW_APPROVAL` |
| Agent weakens protected acceptance oracle | `TEST_ORACLE_CHANGED` |
| Two PRs conflict when combined | `MERGE_GROUP_CONFLICT` |
| Changed path exceeds work-unit scope | `AWU_SCOPE_VIOLATION` |
| Evidence binds a different head | `EVIDENCE_SUBJECT_MISMATCH` |
| Required reviewer is absent | `REQUIRED_REVIEW_MISSING` |
| Author approves its own PR | `SELF_APPROVAL_DENIED` |
| PR checks pass without release approval | `DEPLOYMENT_AUTHORITY_SEPARATE` |

Scenario JSON documents expected teaching outcomes, but the evaluator never reads those expected labels. It builds real candidates and executes the controls.

### 33. Decision semantics

`BLOCKED` means at least one review obligation fails. `ELIGIBLE_FOR_MERGE_REVIEW` means the exact teaching subject satisfied the modeled PR-review checks. It does not mean merged, deployable, released, or production-safe.

### 34. Evaluation population

The lab executes:

- 12 conformance cases;
- 28 labelled evaluation decisions: 8 positive, 12 negative, 4 boundary, and 4 failure/recovery;
- 10 Git-backed review experiments; and
- one deterministic event simulation comparing three strategies over the same synthetic workload.

Populations, numerators, denominators, units, and synthetic inputs are explicit in the JSON report.

---

## Part XI — Productionization

### 35. What the teaching system proves

It proves that, for the generated fixture subjects, the application can derive Git revisions and both rename paths, resolve required scopes from a versioned ownership policy, reject stale/self/forged approvals, resolve authoritative spec and contract digests, execute an independent protected oracle at the exact commit, detect a combined merge conflict, and stop at merge-review eligibility.

### 36. What it does not prove

- GitHub organization or ruleset configuration is correct.
- A reviewer genuinely understood the change.
- The synthetic strategy values predict Northstar's throughput.
- Temporary local Git storage provides production-grade durability.
- A PASS authorizes merge, deployment, release, or a policy exception.
- The examples cover every supply-chain threat or untrusted-code execution risk.
- The fixture's path parser covers adds, modifications, deletions, copies, and renames; production review must additionally govern symlinks, submodules, case-folding, Unicode normalization, and platform-specific filename rules.

### 37. Production upgrades

Production adoption needs authenticated workforce identity, organizational role resolution, durable approval and evidence registries, signed or attestable CI provenance, protected oracle storage, revocation, retention, tamper-evident audit, isolated runners, dependency and artifact controls, repository rulesets, merge queues, cross-repository revision manifests, incident recovery, and monitored outcomes.

---

## Knowledge checkpoint

1. An agent changes an approved requirement, implementation, and tests in one PR. All tests pass. What is the primary concern?

   **Answer:** It may have created a self-confirming but unauthorized behavior change.

2. When is spec-first staging most useful?

   **Answer:** When shared requirements, architecture, or contracts require approval before implementation.

3. A PR is approved at commit A and receives commit B. What happens?

   **Answer:** Reevaluate approval freshness and every affected evidence obligation against B.

4. Two PRs pass separately but fail together. Which control matters?

   **Answer:** Merge-group validation against the combined candidate state.

5. Which metric best compares PR strategies?

   **Answer:** A balanced set including lead time, review effort, rework, meaningful defect detection, integration conflicts, escaped defects, and cost per verified change.

## Final exercise

Three agents created PRs for AI Service, Review Service, and Underwriter UI. AI Service changes the shared contract. Review Service was approved against the previous contract. UI passes local tests.

Design the workflow. Your answer must identify:

1. which approvals and evidence are stale;
2. which intent and contract owners must decide;
3. which work can continue in parallel;
4. the exact repository merge-group checks;
5. the exact cross-repository revision set and system evidence required;
6. the separate merge, deployment, and release authorities; and
7. the stop and escalation conditions.

## Completion criteria

A completed submission includes a strategy ADR, PR dependency graph, protected-path ownership model, trusted approval registry, Git-backed review experiments, exact-revision evidence envelope, strategy comparison with explicit assumptions, and an integration-review handoff that grants no implicit production authority.

## References

- [GitHub: About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub: About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [GitHub: Securely using `pull_request_target`](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
- [Git documentation: `git diff`](https://git-scm.com/docs/git-diff)
- [Git documentation: `git merge-base`](https://git-scm.com/docs/git-merge-base)
- [SLSA provenance](https://slsa.dev/spec/v1.0/provenance)
- [OpenSpec documentation](https://github.com/Fission-AI/OpenSpec/blob/main/docs/README.md)

## Next course

Course 23 covers human approval gates: risk tiers, separation of duties, authenticated single-use decision receipts, expiry, revocation, delegated authority, emergency workflows, and auditability.
