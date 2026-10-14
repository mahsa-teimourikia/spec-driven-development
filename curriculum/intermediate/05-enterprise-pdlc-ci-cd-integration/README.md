# Course 15 — Integrating Spec-Driven Development into Enterprise PDLC and CI/CD

> **Level:** Intermediate path, staff-level depth
>
> **Prerequisites:** Courses 01–14; Git, pull requests, CI/CD, and Python fundamentals
>
> **Case study:** Northstar Mutual change `AI-2310`
>
> **Time:** 5–7 hours including the workshop

Specifications become an operating model only when they influence what may be merged, built, deployed, and accepted in production. This course connects the durable artifacts from Courses 01–14 to enterprise delivery controls without letting a pull request alter its own judge or letting an agent certify its own work.

The central rule is:

> An agent may propose a change and report what it did. Trusted controls validate the claims. Accountable people or services authorize consequential transitions.

## Learning objectives

By the end of the course, you can:

1. map an SDD change through discovery, specification, implementation, PR, merge queue, build, deployment, and runtime observation;
2. name the system of record and accountable owner for every consequential artifact;
3. design risk-adaptive gates without duplicating enterprise policy into every repository;
4. bind a PR to exact specification, context, base, implementation, and effective AI-system revisions;
5. separate implementation completion, verification, integration eligibility, merge authorization, deployment authorization, and production acceptance;
6. validate claim-specific evidence for identity, provenance, independence, freshness, and result;
7. keep trusted validation and authorization outside PR-controlled code;
8. invalidate only the evidence and decisions affected by a changed subject;
9. detect semantic conflicts when individually valid concurrent PRs meet in a merge queue;
10. verify that the artifact deployed is the artifact tested and authorized; and
11. connect runtime invariants to healthy instrumentation and an applicable-population denominator.

## The problem: a good spec does not enforce itself

A repository can contain excellent requirements, ADRs, tasks, and tests while its delivery process still permits unsafe changes. Ordinary CI usually answers questions such as:

- does the code compile?
- do the tests pass?
- does static analysis report a problem?

An enterprise Agentic PDLC must also answer:

- Was this the approved specification revision?
- Was the change planned from the current repository and policy context?
- Did the implementation stay inside its authorized work unit?
- Were protected requirements changed by an authorized owner?
- Is evidence bound to this exact commit and effective AI system?
- Was the verifier independent from the change producer?
- Did the exact merge-queue candidate pass after concurrent changes were composed?
- Was the exact tested artifact built by a trusted platform and deployed?
- Is production telemetry capable of detecting the specified invariant?

Passing tests is evidence for particular technical claims. It is not, by itself, proof of conformance or authorization to merge or deploy.

## 1. From document flow to controlled state transitions

A traditional flow is often drawn as:

```text
idea → ticket → code → PR → tests → merge → deploy
```

That line hides independent states. In a governed flow, each transition has a subject, preconditions, evidence, decision owner, and invalidation rule:

```text
organizational intent
        │
        ▼
effective context ──► approved specification ──► bounded work units
        │                         │                       │
        └──────── exact revisions and provenance ───────┘
                                  │
                                  ▼
PR proposal ──► trusted validation ──► merge-queue candidate
                                  │
                                  ▼
trusted build + provenance ──► deployment authorization
                                  │
                                  ▼
runtime conformance + governed feedback
```

Do not compress these into one `approved: true` flag. A change can be implementation-complete but unverified, verified but unauthorized, merged but not releasable, deployed but not yet accepted, or operationally healthy while its instrumentation is incapable of observing the relevant population.

## 2. Systems of record and ownership

The same concept may appear in several tools, but only one system should be authoritative for each decision.

| Concern | Typical system of record | Accountable owner | Delivery use |
| --- | --- | --- | --- |
| Business intent | Product/Jira system | Product owner | establishes outcome and scope |
| Approved behavior | Versioned specification repository | Requirement/domain owner | determines conformance claims |
| Architecture decision | ADR repository | Architecture owner | constrains design and exceptions |
| Enterprise policy | Policy/control repository | Policy owner | selects applicable obligations |
| Implementation | Product repository | Engineering owner | proposes executable change |
| Test/evaluation result | Trusted evidence service | Verification owner | supports a named claim |
| Merge authorization | Source-control control plane | Repository owner | permits baseline mutation |
| Build identity | Artifact registry/provenance service | Platform owner | binds artifact to source/build |
| Deployment authorization | Deployment control plane | Environment/service owner | permits environment mutation |
| Runtime conformance | Observability/control system | Service and control owners | measures deployed behavior |

Links and caches are useful; copied authority is dangerous. A PR description can reference an approved requirement but does not become the requirement authority. A generated manifest can claim that policy was resolved, but the trusted gate must compare it with the current policy registry.

## 3. Four control boundaries

### Boundary 1 — specification readiness

The change may enter implementation only when its behavioral and non-functional obligations are clear enough for the selected risk tier. Readiness is capability-scoped: an unresolved question should block the affected capability, not automatically freeze unrelated work.

### Boundary 2 — implementation conformance

The authoritative diff must remain within the approved work-unit scope. Applicable requirements need implementation and evidence ancestry. Protected requirement semantics may change only through their owning authority.

### Boundary 3 — integration authorization

A finding-free validation result means “eligible for an accountable integration decision.” It does not mutate the baseline. Merge authorization is a distinct, short-lived, exact-subject decision.

### Boundary 4 — deployment authorization

Deployment is authorized for an immutable artifact digest, environment, system revision, and time window. Source approval cannot authorize an arbitrary later rebuild.

## 4. The SDD change envelope

The lab uses a change envelope rather than a long PR template. The envelope composes references to authoritative artifacts:

```json
{
  "change_id": "AI-2310",
  "specification_revision": "AI-2310-spec@7",
  "context_digest": "sha256:context-2310-r12",
  "base_revision": "8f58f25",
  "policy_revisions": ["AI-GOV@12", "ARCH@9", "SEC@31"],
  "risk_tier": "high",
  "authorized_paths": ["src/document_classifier.py"],
  "open_decisions": []
}
```

This is a claim, not proof. The trusted validator independently retrieves the current specification revision, context, base, and policy set. It compares authoritative changed paths with the approved work unit instead of accepting an agent's summary of the files it edited.

### Bind all consequential subjects

At minimum, bind evidence and decisions to:

- change identity;
- exact source commit;
- approved specification revision;
- effective-context digest;
- effective AI-system revision; and
- for deployment, artifact digest and environment.

The **effective AI-system revision** is broader than application code:

```text
application + model + prompts + retrieval/index + tools + policy + runtime configuration
```

Changing a prompt or model alias can invalidate behavioral evidence even when the Git commit is unchanged.

## 5. Pull requests as controlled proposals

A PR should make review cheaper without pretending that metadata is authoritative. For `AI-2310`, its envelope provides:

- the approved change and specification revision;
- the resolved policy and architecture context;
- the bounded work unit and authoritative changed paths;
- requirement → implementation → evidence links;
- the exact effective AI-system revision;
- unresolved decisions and requested transition; and
- references to evidence rather than unaudited pasted output.

Useful PR status is derived, not self-declared:

| State | Meaning |
| --- | --- |
| `IMPLEMENTATION_COMPLETE` | executor stopped and produced the requested artifacts |
| `VERIFIED` | independent claim-specific checks passed for an exact subject |
| `ELIGIBLE_FOR_INTEGRATION_REVIEW` | all required gates are complete and non-blocking |
| `AUTHORIZED_FOR_INTEGRATION` | an authorized receipt permits the exact merge subject |
| `AUTHORIZED_FOR_DEPLOYMENT` | an authorized receipt permits an exact artifact/environment pair |
| `PRODUCTION_ACCEPTED` | defined runtime obligations passed for the observation window |

None implies the next state automatically.

## 6. Staleness and selective invalidation

“The spec changed” is not one failure. A change may affect different descendants:

| Changed subject | Invalidate at minimum |
| --- | --- |
| Requirement semantics | affected design, tasks, implementation claims, evidence, receipts |
| Architecture constraint | affected design, work units, implementation evidence |
| Policy applicability | effective context and every affected downstream decision |
| Code commit | implementation, technical, security, and behavioral evidence |
| Prompt/model/retrieval configuration | AI behavior evidence and deployment authorization |
| Merge base | conflict analysis and exact merge-candidate checks |
| Artifact digest | provenance verification and deployment authorization |
| Runtime instrumentation | production-conformance conclusions |

Selective invalidation prevents both unsafe reuse and wasteful full restarts. The dependency graph—not a global “dirty” flag—should determine what must run again.

## 7. A layered, risk-adaptive gate model

The lab evaluates nine explicit gates with `PASS`, `REVIEW`, `BLOCK`, or `NOT_APPLICABLE`:

1. `specification_readiness`
2. `implementation_conformance`
3. `technical_quality`
4. `evidence_integrity`
5. `control_provenance`
6. `integration_readiness`
7. `integration_authorization`
8. `deployment_authorization`
9. `runtime_conformance`

Every required gate must report. A missing gate is not a pass. Aggregation remains intentionally modest:

- any `BLOCK` → `BLOCKED`;
- otherwise any `REVIEW` → `REQUIRES_REVIEW`;
- otherwise → `ELIGIBLE_FOR_INTEGRATION_REVIEW`.

The aggregate never says “merge” or “deploy.” Those are authorized transitions.

### Risk changes depth, not truth

A documentation typo may need source checks and an owner review. A high-risk AI change may additionally require policy resolution, safety evaluation, protected-path ownership, independent security evidence, trusted build provenance, staged deployment, and runtime observation. Both still need correct identity and truthful evidence.

Avoid two extremes:

- one enormous workflow that every repository copies and slowly drifts; and
- each repository inventing its own interpretation of company controls.

Prefer a central control plane with versioned policy bundles and reusable, pinned validation components. Repositories declare facts and references; the control plane determines current applicability and gate requirements.

## 8. The CI trust boundary

If a PR can change the validator that judges the same PR, a green check may only prove that the PR weakened its judge.

A secure arrangement separates:

```text
untrusted tenant data                 trusted control plane
────────────────────                 ─────────────────────
PR code and tests          ────────► protected validator revision
change manifest            ────────► current policy/authority registries
self-reported completion   ────────► independent runners and evaluators
requested transition       ────────► receipt issuer/consumer
```

In GitHub Actions, treat PR content and event fields as untrusted input. Use least-privilege tokens, protect workflow files, pin dependencies, and do not combine privileged triggers with checkout/execution of untrusted PR code. The lab models control provenance as a protected repository and revision; it does not claim that a JSON value authenticates a real CI service.

Required status checks and rulesets are enforcement surfaces, not the policy source. A check name without protected provenance is merely a label.

## 9. Evidence as a typed, claim-specific manifest

An evidence record should say what it supports, who produced it, and which exact subject it observed:

```json
{
  "claim_id": "CLM-PROMPT-INJECTION",
  "result": "PASS",
  "producer": "northstar/security-verifier@5",
  "independent": true,
  "expires_at": "2026-10-20T00:00:00Z",
  "subject": {
    "change_id": "AI-2310",
    "commit": "pr-head-b91c6d2",
    "specification_revision": "AI-2310-spec@7",
    "system_revision": "sha256:system-app43-model17-prompt12-retrieval8-tools6-policy12"
  }
}
```

Validation asks:

1. Is this claim required for this risk profile?
2. Is the producer approved for this claim type?
3. Is the producer independent of the subject's author where required?
4. Does the record bind the exact change, commit, specification, and system revision?
5. Is the result acceptable and still fresh?
6. Has any dependency changed since production?

A test report for the wrong commit is not partial credit. A generic “tests passed” record cannot satisfy a safety claim. An executor's completion report is valuable operational telemetry, but it cannot independently prove correctness.

## 10. AI evaluation as a delivery gate

Probabilistic systems add evidence that conventional unit tests do not replace. A useful evaluation contract specifies:

- population and inclusion/exclusion rules;
- dataset and label provenance;
- split and contamination controls;
- metrics, slices, uncertainty, and owner-approved thresholds;
- model, prompt, retrieval, tool, and policy revisions;
- deterministic judge code or governed human rubric;
- failure examples and limitations; and
- the decision the evidence is allowed to support.

An AI evaluation gate should fail closed when the evaluated system revision differs from the candidate. It should not let a model grade its own output under an undisclosed prompt and call the result independent.

## 11. Merge queues and semantic composition

Two PRs can be individually valid and textually conflict-free while jointly invalid. They may change different files but weaken the same invariant, exhaust the same budget, change coupled contracts, or rely on incompatible policy interpretations.

Merge-queue validation should run against the exact queued merge candidate and include:

- current base and specification checks;
- invalidation since the earlier PR run;
- cross-change requirement and architecture conflict analysis;
- regenerated claim/evidence requirements; and
- the same protected control revision required by the ruleset.

GitHub documents the `merge_group` event for checks on merge-queue candidates. A workflow that runs only on `pull_request` can leave the queue without the required result.

## 12. Build provenance and immutable artifact identity

Source conformance does not prove artifact identity. The build platform should generate provenance that binds output digest to source and build inputs. Consumers must verify the provenance rather than merely store it.

The lab checks:

- a trusted builder identity;
- a verified provenance signature signal;
- provenance subject digest equals the built artifact digest; and
- deployment request and receipt name that same digest.

SLSA v1.2 distinguishes increasing Build-track guarantees. Provenance existence helps prevent mistakes; higher levels add hosted signing and stronger build-platform protections. Course 15 models the verification relationship, not a real SLSA certification.

## 13. Deployment receipts and rollback

A deployment receipt is short-lived, single-use, and exact-subject. It binds:

- change and source commit;
- specification and effective AI-system revisions;
- artifact digest;
- target environment;
- authorized actor/issuer;
- expiry, revocation, state, and version.

The receipt consumer must update state atomically. Without that property, two workers could both observe `AVAILABLE` and deploy twice. The lab uses a lock to make the teaching primitive explicit; a production system needs durable transactional or compare-and-swap semantics.

Rollback is another governed transition. Pre-authorize known-safe rollback artifacts and record the runtime conditions that trigger rollback. “Redeploy something old” is not a recovery design.

## 14. Runtime conformance

Specifications should generate observable obligations. For example:

> Every recommendation in the applicable production population shall retain a human-review-required state before an authoritative policy decision.

Runtime evidence needs both the numerator and the denominator:

```text
violation rate = invariant violations / applicable decisions observed
```

Zero recorded violations is not reassuring if instrumentation is unhealthy, sampling excludes the risky population, correlation IDs are missing, or the deployed system revision is unknown. Runtime monitoring supports bounded operational claims; it cannot prove all unobserved behavior or repair a wrong requirement.

NIST AI RMF describes governance as cross-cutting and risk management as continuous across the lifecycle. Course 15 applies that idea by carrying traceable obligations through delivery and back from production, without treating the framework as a checklist or certification.

## 15. Failure patterns and recovery

| Failure | Unsafe response | Governed response |
| --- | --- | --- |
| Policy changes mid-implementation | continue because code is nearly done | recompute applicability; selectively invalidate affected context, work, and evidence |
| CI passes but requirement was weakened | trust green tests | compare protected semantic identity; route requirement change to its owner |
| Agent changes tests to match wrong behavior | accept code/test consistency | retain independent or owner-controlled oracles and mutation evidence |
| PR modifies its validator | run new validator from PR | use a protected validator revision; review control change separately |
| Merge queue creates semantic conflict | rely on Git conflict detection | re-evaluate exact merge candidate and block affected claims |
| Artifact rebuilt after approval | deploy by tag | verify immutable digest and provenance against authorization receipt |
| Zero runtime violations | declare success | verify instrumentation health, coverage, denominator, and system identity |

Recovery is a state transition, not manual erasure. Record why evidence was invalidated, which owner dispositioned the change, and which new subject must be verified.

## 16. Practical lab — `northstar-sdd-delivery`

Northstar's `AI-2310` adds document-classification behavior to the Underwriter Assistant. You receive:

- a trusted control-plane fixture;
- a safe reference delivery package;
- an unsafe candidate whose ordinary technical tests still pass;
- nine deterministic gates;
- ten golden scenarios; and
- 64 labelled control mutations.

Run the lab:

```bash
python3 curriculum/intermediate/05-enterprise-pdlc-ci-cd-integration/northstar-sdd-delivery/lab.py
```

Expected high-level result:

```text
reference:        ELIGIBLE_FOR_INTEGRATION_REVIEW
unsafe candidate: BLOCKED
technical quality on unsafe candidate: PASS
golden scenarios: 10 / 10
control mutations: 64 / 64
```

That contrast is the point: technically green is not delivery-safe.

Continue with the [guided notebook](northstar-sdd-delivery/enterprise_pdlc_delivery.ipynb), then complete the [workshop](northstar-sdd-delivery/README.md) before reading the reference package.

## 17. Production architecture

Do not copy the teaching script into every repository. A production platform usually needs:

```text
repository adapters ──► change/evidence API ──► policy and authority resolver
         │                         │                         │
         ▼                         ▼                         ▼
untrusted execution       trusted verification       decision/receipt service
         │                         │                         │
         └──────────── artifact/provenance registry ────────┘
                                   │
                                   ▼
                         deployment + runtime feedback
```

Platform qualities include:

- authenticated workload and human identities;
- immutable or tamper-evident event history;
- versioned policy bundles and explainable decisions;
- idempotent APIs and atomic receipt consumption;
- least-privilege credentials and isolated untrusted execution;
- retention, redaction, privacy, and regional constraints;
- availability and recovery targets for gates on the critical path;
- rollout, exception, break-glass, and control-upgrade procedures; and
- metrics that separate delivery speed, control effectiveness, and review burden.

## 18. Progressive adoption

1. **Observe:** generate change and evidence manifests without blocking delivery.
2. **Warn:** report stale identity, scope, and evidence findings with owner routing.
3. **Block narrow invariants:** protect current spec identity, protected paths, and artifact digest.
4. **Add risk profiles:** require deeper evidence for higher-consequence changes.
5. **Move authorization outward:** issue exact-subject merge and deployment receipts.
6. **Close the loop:** connect runtime signals to invalidation and governed specification evolution.

Measure escaped control violations, invalid-evidence reuse, revalidation lead time, review depth, exception age, rollback readiness, false block rate, and time from a policy change to affected-change identification. Agent utilization is not the outcome.

## 19. Staff-level design checkpoint

You are reviewing a high-risk PR. Unit tests, static analysis, and the model evaluation pass. The PR also updates the workflow that produces the required `sdd-conformance` check. Its evidence manifest names the current commit, but the evaluation was run against yesterday's prompt bundle. The merge queue contains another PR changing the human-review invariant.

Before integration eligibility, identify:

1. which three independent subjects have changed;
2. which evidence or decisions must be invalidated;
3. which control must run from a protected revision;
4. which semantic conflict requires an accountable disposition; and
5. why a green test suite cannot answer any of those authority questions.

**Checkpoint answer:** control provenance is invalid because the PR changes its own judge; behavioral evidence is bound to the wrong effective AI-system revision; and the merge candidate has a semantic conflict. Re-run the protected validator and behavioral evaluation on the exact queued candidate after the requirement owner resolves the conflict. Only then can the change become eligible for an integration decision. No agent or aggregate score may authorize the merge.

## 20. Completion criteria

You have completed Course 15 when you can:

- explain every gate result in the reference and unsafe packages;
- make all ten golden scenarios produce the expected failure code;
- preserve 64/64 mutation detection;
- issue and atomically consume an exact-subject integration receipt;
- demonstrate that an authorized source commit cannot authorize a substituted artifact;
- distinguish synthetic fixture evidence from production assurance; and
- sketch a central platform that preserves repository autonomy without duplicating policy.

## References

- [GitHub Docs — Secure use reference for GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Docs — Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub Docs — Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [GitHub Docs — `merge_group` workflow event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)
- [SLSA v1.2 specification](https://slsa.dev/spec/v1.2/)
- [SLSA v1.2 — Verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [GitHub Spec Kit](https://github.github.com/spec-kit/)
- [OpenSpec](https://github.com/Fission-AI/OpenSpec)

## Key takeaways

- A specification is enforceable only when delivery controls consume its identity and claims.
- The PR is untrusted tenant input, including its tests, manifests, and workflow changes.
- Evidence must be claim-specific, independent where necessary, fresh, and bound to the exact subject.
- Validation determines eligibility; accountable authority permits merge and deployment.
- Merge, build, deploy, and runtime acceptance are different states with different subjects.
- The delivered artifact must be the tested, provenance-verified, authorized artifact.
- Runtime conformance requires healthy instrumentation and an applicable-population denominator.
- A reusable enterprise control plane is safer and more maintainable than policy copied into each repository.
