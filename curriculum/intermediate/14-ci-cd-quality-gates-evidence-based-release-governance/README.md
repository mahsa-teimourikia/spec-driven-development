# Course 24 — CI/CD Quality Gates and Evidence-Based Release Governance

> Enterprise Spec-Driven Development · Part IV: Agentic PDLC · Course 24 of 38

**Level:** Advanced / Staff AI Scientist and AI Technical Lead
**Prerequisites:** Courses 14–17 and 20–23
**Case study:** Northstar Mutual — production delivery of the AI Underwriting Assistant
**Practical stack:** Python, GitHub Actions concepts, OpenSpec, SQLite, SLSA/in-toto concepts, SBOMs, Sigstore concepts, OPA/Rego, and OpenTelemetry concepts

## Why this course matters

Course 23 made human approval an enforceable authorization boundary. That is necessary, but it does not prove that the approved software and AI configuration reached production.

A coding agent can produce a valid implementation, a pull request can pass every check, and a release manager can approve deployment—yet production may still run a different image, model, prompt, retrieval index, tool policy, or database schema. A mutable tag, a post-approval rebuild, an untrusted evidence producer, or an environment-specific configuration change can break the chain between intent and runtime behavior.

The central principle is:

> Build once, verify the exact artifact and effective AI configuration, promote by identity, authorize the exact deployment, and verify actual production state.

The local lab exercises this principle without cloud credentials. It produces real artifact bytes, authenticated teaching provenance, a parsed SBOM, executable functional and AI evaluations, manifest-bound approvals, transactional deployment state, protected rollout invariants, unknown-outcome reconciliation, and recovery records. It does **not** claim Sigstore, SLSA, or production certification.

## Learning objectives

By the end of this course, you should be able to:

1. Design risk-adaptive quality gates for agent-generated changes.
2. Separate source verification, build provenance, artifact integrity, test evidence, deployment authorization, and runtime conformance.
3. Explain the complementary roles of SLSA, in-toto attestations, SBOMs, Sigstore, OPA/Rego, and OpenTelemetry.
4. Bind requirements, tests, AI evaluations, approvals, and deployment evidence to exact revisions.
5. Keep untrusted pull-request execution away from protected credentials and authoritative evidence production.
6. Define an effective AI release identity spanning software, model, prompt, retrieval, tools, schema, dataset, and evaluation contract.
7. Promote immutable artifacts without assuming environment configuration is identical.
8. Distinguish deployment success from runtime acceptance.
9. Handle `FAILED` and `UNKNOWN_OUTCOME` without unsafe blind retries.
10. Design rollback, containment, forward repair, and business-state reconciliation.

## Run the course

From the repository root:

```bash
python3 curriculum/intermediate/14-ci-cd-quality-gates-evidence-based-release-governance/northstar-release-control/lab.py
python3 -m unittest tests.test_course_24 -v
```

Then open the guided [release-governance notebook](northstar-release-control/release_governance.ipynb) from the `northstar-release-control` directory.

---

# Part I — The enterprise delivery trust chain

## 1. Green CI is not production readiness

For Northstar's AI-2500 Broker Document Review feature, a green pull request may establish that a particular source revision passed selected checks. It does not, by itself, establish:

- that the checks were appropriate for the change risk;
- that the trusted builder used the reviewed revision;
- that the artifact was not replaced after verification;
- that the effective model, prompt, retrieval, and tool configuration were evaluated;
- that the approval names the artifact and environment being deployed;
- that the deployment effect occurred exactly once; or
- that production behavior satisfies protected invariants.

The delivery chain has distinct trust boundaries:

```text
approved specification
        ↓
verified source revision
        ↓
trusted build and authenticated provenance
        ↓
verified immutable artifact + effective AI manifest
        ↓
authorized promotion and deployment
        ↓
runtime acceptance or governed recovery
```

Passing one stage never silently authorizes the next.

## 2. Five evidence families

| Evidence | Establishes | Does not establish |
|---|---|---|
| Source | What revision and diff were reviewed | Which artifact was deployed |
| Build provenance | Where, when, and how an artifact was produced | Business or model correctness |
| Test/evaluation | Results for a named subject and population | Correctness outside that subject and population |
| Approval | Who authorized an exact action, target, and expiry | Whether execution succeeded |
| Runtime | What the deployed system did during an observation window | That the behavior was originally authorized |

A mature control plane links all five while preserving their different meanings.

## 3. The artifact identity problem

If CI tests `sha256:AAA` but production deploys `northstar/ai-service:latest`, the tag may later resolve to `sha256:BBB`. Evidence for `AAA` says nothing about `BBB`.

Use immutable digests as authoritative artifact identity. Tags can remain human-friendly locators, but the resolver must bind them to a digest and reject disagreement.

---

# Part II — Supply-chain evidence

## 4. Complementary controls

| Control | Purpose | Important boundary |
|---|---|---|
| SLSA | Framework and formats for improving source/build supply-chain integrity | A level or provenance record does not prove application correctness |
| in-toto attestation | Binds a typed predicate to artifact subjects | A statement remains a claim until its envelope/producer is authenticated |
| SBOM | Inventory of components and versions | Inventory alone is not vulnerability or policy acceptance |
| Sigstore/Cosign | Signing and identity-based verification for artifacts and attestations | A valid signature can still cover an unacceptable build |
| OPA/Rego | Policy decisions over structured facts | OPA does not authenticate input facts for you |
| OpenTelemetry | Traces, metrics, logs, and context for observable execution | Telemetry presence does not establish behavioral correctness |

## 5. Provenance is a policy input, not a magic certificate

Build provenance should bind the artifact subject to source revision, builder identity, workflow revision, dependency state, and other required build facts. Verification has two layers:

1. Authenticate the producer and statement.
2. Evaluate whether the authenticated facts satisfy organizational policy.

A correctly signed artifact built from an unapproved branch must still be rejected.

The lab uses an HMAC-authenticated teaching record so that producer authentication is executable offline. Production systems should use approved provenance schemas and a protected trust root; the HMAC fixture is not presented as Sigstore or SLSA certification.

## 6. SBOMs and dependency policy

The lab parses `requirements.lock` into a deterministic SBOM. The release gate then requires SBOM evidence for the exact artifact digest. This demonstrates inventory and subject binding.

A production dependency gate also needs:

- trustworthy component discovery;
- package and source provenance;
- vulnerability and license policy;
- exception ownership and expiry;
- reachability or exploitability context where approved;
- refreshed findings when vulnerability intelligence changes.

---

# Part III — Secure CI architecture

## 7. Separate untrusted and trusted execution

Use at least two zones:

```text
Untrusted PR CI                          Trusted release CI
----------------                         ------------------
compile, lint, unit tests                 protected build
safe static analysis                      provenance / signing
sandboxed evaluations                     evidence verification
no release credentials                    artifact publication
no deployment authority                   approval + deployment
```

Untrusted results can be candidates for later verification. They cannot manufacture authoritative release evidence.

## 8. Minimal PR permissions

An illustrative workflow might use `pull_request`, read-only repository access, pinned action revisions, bounded time, locked dependencies, and an ephemeral runner. Placeholder action SHAs are not a finished security control; organizations must pin verified immutable revisions and maintain them.

GitHub's official guidance treats `pull_request_target` as sensitive because it runs with the base repository's trust. Never combine privileged context with checkout and execution of attacker-controlled pull-request code. Separate metadata operations from untrusted code execution.

## 9. Protect the evidence producer

Agent-generated code may modify tests, build scripts, workflows, thresholds, datasets, or policy. A secure design distinguishes:

- candidate-authored artifacts;
- independently controlled acceptance criteria;
- protected workflow and builder identities;
- authenticated evidence records;
- repository or environment rules that control authoritative changes.

A file named `test-results.json` is not trusted merely because its schema is valid.

---

# Part IV — Risk-adaptive quality gates

## 10. Gates verify obligations

Each gate should answer:

1. Which requirement or risk does it address?
2. Which exact subject was evaluated?
3. Which producer generated the evidence?
4. Which policy revision and threshold apply?
5. What happens when evidence is missing, stale, failed, or inconclusive?

Northstar uses these logical gates:

| Gate | Verification | Blocking example |
|---|---|---|
| Specification | Approved normative revision | Unknown requirement or unauthorized weakening |
| Source | Exact revision and authorized diff | Protected workflow changed without review |
| Build | Trusted builder and provenance | Untrusted branch, workflow, or builder |
| Dependencies | Subject-bound SBOM and policy | Missing SBOM or prohibited dependency |
| Functional | Contract and acceptance behavior | Required scenario fails |
| AI quality | Approved evaluation population and thresholds | Stale model evidence or invariant failure |
| Security | Authorization and adversarial invariants | Tenant or tool-boundary violation |
| Release | Exact manifest, environment, approvals | Receipt mismatch, expiry, or replay |
| Runtime | Operational and behavioral rollout checks | Human-review bypass or protected mutation |

## 11. Risk selection is protected policy

An agent must not lower its own risk tier. The trusted control plane resolves applicable risk and rejects unknown tiers or gates.

| Change | Typical emphasis |
|---|---|
| Documentation correction | Formatting, links, repository integrity |
| Internal refactor | Contract, regression, dependency, build evidence |
| Consequential AI behavior | Full functional, security, AI evaluation, dual approval, rollout, recovery |

Risk adaptation means selecting justified controls—not weakening universal protected invariants.

---

# Part V — AI-specific release identity and evaluation

## 12. Software tests are insufficient

An AI component can return valid JSON, meet latency limits, and pass API tests while incorrectly routing ambiguous documents around human review. AI release evidence therefore includes behavioral populations and protected invariants in addition to conventional software tests.

## 13. Evaluation layers

For AI-2500, evaluate:

- schema and contract conformance;
- evidence provenance and authorization;
- classification correctness on an owned population;
- ambiguity handling and abstention;
- cross-tenant rejection;
- prompt-injection resistance at protected tool boundaries;
- retry and state integrity;
- operational latency and cost budgets.

The metric contract must define population, numerator, denominator, unit, direction, slices, and aggregation. Aggregate accuracy must not hide failures on high-consequence slices.

## 14. Effective AI release manifest

Container identity is only one release input. The effective manifest includes:

```yaml
release_id: AI-2500-R17
source_commit: 4c0f3b2...
artifact_digest: sha256:...
model_revision: model-v12
prompt_digest: sha256:prompt-v7
retrieval_revision: index-2026-10-30
tool_policy_revision: TOOL-POLICY@9
schema_revision: DB-SCHEMA@17
evaluation_contract_revision: EVAL-DOC-2500@3
dataset_digest: sha256:dataset-underwriting-eval-v4
environment: production
```

The trusted resolver must verify these references. Including them in YAML does not make them true.

## 15. Targeted evidence invalidation

Evidence validity is a dependency relation:

\[
E = f(A, M, P, R, T, S, D, C)
\]

where artifact `A`, model `M`, prompt `P`, retrieval `R`, tool policy `T`, schema `S`, dataset `D`, and contract `C` can invalidate different evidence sets.

| Changed input | Likely reassessment |
|---|---|
| Application artifact | Functional, security, integration, AI behavior |
| Model | AI quality, safety, latency, cost |
| Prompt | AI behavior, tool use, grounding |
| Retrieval | Grounding, coverage, data authorization |
| Tool policy | Authorization and adversarial security |
| Schema | Migration, persistence, compatibility |
| Dataset/contract | Metric meaning, thresholds, population validity |

Do not rerun everything blindly, but do not reuse evidence without an approved impact model.

---

# Part VI — Build once and immutable promotion

## 16. Promote the same artifact

Rebuilding separately for staging and production can produce different bytes even from the same source. Build once, verify the artifact, and promote its immutable digest.

This does **not** mean runtime configuration is identical. A staging image can use a staging model or index while production uses protected production revisions. Environment-specific configuration is a separately governed part of effective release identity.

## 17. Attestation verification pipeline

```text
attestation received
        ↓
authenticate envelope / producer identity
        ↓
validate builder, workflow, source, and predicate
        ↓
match subject digest to actual artifact bytes
        ↓
resolve other revision-bound evidence
        ↓
evaluate release policy
```

Hash comparison proves byte identity. It does not authenticate who made the statement or whether the build is allowed.

---

# Part VII — Policy-as-code and approval

## 18. Policy consumes verified facts

OPA/Rego is useful for expressing release decisions over structured data, but the decision is only as trustworthy as its inputs. The lab's Python boundary authenticates producer identity and resolves records before applying policy. The included Rego file illustrates the equivalent composition; it is not used as a cosmetic claim of enforcement.

The trusted sequence is:

```text
collect → authenticate → validate applicability → evaluate policy → authorize → execute → verify
```

## 19. Eligibility is not deployment authority

A passing gate produces `ELIGIBLE_FOR_RELEASE_REVIEW`. It does not deploy automatically.

Production deployment requires distinct, authenticated release and AI-governance approvals bound to:

- release ID and full manifest digest;
- target environment;
- approver principal and role;
- issuance, expiry, and state.

Receipts are consumed transactionally. Reuse and changed-subject attempts fail.

---

# Part VIII — Progressive delivery and runtime verification

## 20. Deployment success is not release success

A deployment API can report healthy containers while the AI feature violates a protected behavior. A release becomes `ACTIVE` only after runtime acceptance.

Illustrative rollout stages include dark launch, canary, expansion, and full exposure. Percentages and observation windows must be risk-owned; a short canary may have no power to detect rare failures.

## 21. Operational and behavioral evidence

Use operational telemetry for availability, latency, errors, and request flow. Combine it with behavioral checks for human-review routing, authorization, protected mutations, grounding, and approved outcome samples.

OpenTelemetry can correlate traces, metrics, logs, and context, but telemetry collection alone does not prove correct classification. Avoid placing document content, secrets, or unnecessary personal data in telemetry.

## 22. Protected rollout failure

If an ambiguous document bypasses required review, the lab:

1. records `HUMAN_REVIEW_BYPASS`;
2. transitions the operation to `HALTED`;
3. disables the feature; and
4. preserves manual review.

The control comes from observed state, not a prefilled `canary_passed: false` flag.

---

# Part IX — Unknown outcomes and idempotency

## 23. `FAILED` is different from `UNKNOWN_OUTCOME`

A timeout after calling an external deployment API does not prove failure. Blind retry can duplicate or conflict with a real deployment.

Use a stable logical operation ID, record `UNKNOWN_OUTCOME`, inspect the actual target environment, and reconcile before retry. The lab simulates a timeout after the environment mutation, then verifies the observed manifest and moves the operation to `VERIFYING` without a second deployment.

Authorization or policy denial is terminal. Only approved transient failures should be retried, with a bounded attempt policy.

---

# Part X — Rollback, containment, and recovery

## 24. Rollback is not only the container

Restoring `sha256:AAA` while leaving model v13, prompt v8, or a new retrieval index active does not restore the previous effective AI system.

| Change | Typical recovery |
|---|---|
| Application image | Redeploy a previous verified digest |
| Model/prompt | Restore supported approved revisions |
| Retrieval index | Restore a prior index or alias |
| Feature flag | Contain by disabling the capability |
| Database schema | Expand-and-contract or governed forward repair |
| External communication | Compensating action where possible |
| Authoritative business mutation | Reconciliation and accountable correction |

Rollback, roll-forward, and containment are distinct mechanisms.

## 25. Complete recovery identity

The lab first requires a previously verified target manifest, then compares every target dependency. Restoring only the image yields `RECOVERY_INCOMPLETE`. Restoring the complete manifest while leaving business obligations open yields `RECOVERY_IN_PROGRESS`. Only a complete identity plus required reconciliation can become `RECOVERED`.

Required reconciliation includes manual-review restoration, protected-mutation disablement, and production health checks. An open historical-submission audit keeps recovery in progress.

The fixture evaluates recovery eligibility; it does not model a separate emergency recovery approval. A production adapter must enforce whichever release or incident authority applies before performing recovery effects.

---

# Part XI — Executable lab architecture

## 26. What the lab proves

The [Northstar release-control fixture](northstar-release-control/README.md) includes:

- deterministic artifact construction from real source bytes;
- artifact digest recomputation at release time;
- authenticated teaching provenance and protected builder policy;
- a parsed SBOM;
- executable classifier, ambiguity, and prompt-injection checks;
- revision-bound evidence dependencies;
- risk-derived gate selection;
- manifest-bound dual approval and atomic consumption;
- durable deployment operations and environment state;
- runtime activation or containment;
- unknown-outcome reconciliation; and
- complete-manifest recovery decisions.

## 27. Release state machine

```text
CANDIDATE
   ├── BLOCKED
   └── ELIGIBLE_FOR_RELEASE_REVIEW
          └── AUTHORIZED → DISPATCHED
                                ├── UNKNOWN_OUTCOME → reconcile → VERIFYING
                                └── VERIFYING
                                      ├── ACTIVE
                                      └── HALTED

HALTED → RECOVERY_INCOMPLETE | RECOVERY_IN_PROGRESS | RECOVERED
```

The local deployment effect and database transition share one SQLite transaction. A remote production adapter would need durable outbox/queue delivery, idempotency, authenticated target-state observation, bounded retries, and reconciliation.

## 28. Golden scenarios

The lab executes twelve cases:

1. exact verified artifact reaches `ACTIVE`;
2. artifact bytes modified after testing are blocked;
3. untrusted builder provenance is rejected;
4. required SBOM absence blocks release;
5. failed dependency evidence blocks release;
6. model drift invalidates AI evaluation;
7. prompt drift invalidates AI evaluation;
8. an unapproved tool policy is rejected;
9. approval for a different manifest is rejected;
10. canary review bypass halts and contains rollout;
11. image-only rollback is incomplete; and
12. open state reconciliation prevents recovery completion.

The adversarial suite adds unknown identities, unapproved branches, self-reported evidence, stale retrieval/dataset evidence, expired and missing approvals, replay, missing runtime observations, unknown outcome, and cross-tenant behavior.

---

# Part XII — Staff-level design exercise

## 29. The release that passed every test

AI-2500 has approved requirements, reviewed source, passing tests, verified provenance, an SBOM, AI evaluation for model v12, and production approval. Production configuration points to model v13.

Design the decision:

1. Identify evidence that remains valid.
2. Identify model-dependent evidence that is stale.
3. Decide whether deploying v12 is allowed under the approved manifest.
4. Explain how v13 could become eligible without rebuilding unrelated components.
5. Define the exact release identity and approval subject.
6. Define the rollout and recovery conditions.

A strong answer neither rebuilds everything blindly nor reuses model-dependent evidence without justification.

## 30. Workshop decisions

Complete the [starter release design](northstar-release-control/workshop/starter/release-design.json). You must decide:

- trusted and untrusted workflow boundaries;
- release-manifest identity;
- evidence dependencies and invalidation;
- approval subject and expiry;
- unknown-outcome reconciliation;
- rollout invariants; and
- complete recovery conditions.

Compare your result with the [reference design](northstar-release-control/reference/release-design.json). The reference is a teaching solution, not production authorization.

---

# Part XIII — Productionization checklist

Before adapting the lab to production, add:

- a protected identity provider, KMS/HSM-backed trust roots, and key rotation;
- approved SLSA/in-toto schemas and Sigstore verification policy;
- protected, ephemeral builders and isolated untrusted CI;
- registry immutability, retention, and replication controls;
- verified workflow/action pinning and dependency hermeticity where required;
- independent vulnerability, license, secret, and malware controls;
- durable workflow orchestration, outbox delivery, idempotency, and reconciliation;
- environment-specific authorization and policy distribution;
- statistically justified AI evaluation and rollout populations;
- independently protected evidence and audit storage;
- privacy-aware telemetry and retention;
- database migration and business-state recovery plans; and
- exercised incident, containment, and rollback procedures.

## Knowledge check

1. Why is a mutable image tag insufficient as release identity?
2. Why can a valid signature still describe an unacceptable build?
3. Which AI release inputs can invalidate model-behavior evidence without changing application bytes?
4. What must happen after an external deployment timeout?
5. Why can image rollback leave the effective AI system unsafe?

Use the cumulative [quiz](../../../quiz/index.html) for scored questions.

## Authoritative references

- [SLSA specification v1.2](https://slsa.dev/spec/v1.2/)
- [SLSA provenance](https://slsa.dev/spec/v1.2/provenance)
- [in-toto Attestation Framework v1 specification](https://github.com/in-toto/attestation/blob/main/spec/v1/README.md)
- [Sigstore Cosign signature verification](https://docs.sigstore.dev/cosign/verifying/verify/)
- [GitHub Actions security guidance](https://docs.github.com/en/actions/how-tos/secure-your-work)
- [Securely using `pull_request_target`](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
- [Open Policy Agent policy language](https://www.openpolicyagent.org/docs/policy-language)
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

## Course boundary

This course produces `ELIGIBLE_FOR_ACCOUNTABLE_REVIEW` evidence. It does not approve an organizational release policy, certify a builder, authenticate the synthetic external model/prompt/retrieval identifiers against real registries, authorize a real production deployment or recovery, or establish production model quality.
