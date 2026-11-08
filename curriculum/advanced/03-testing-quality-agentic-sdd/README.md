# Course 27 — Testing, Quality Engineering, and Independent Verification for Agentic SDD

> Enterprise Spec-Driven Development · Part V: Enterprise Controls · Course 27 of 38

**Level:** Advanced / Staff AI Scientist, Staff Engineer, Quality Architect, Platform Engineer, and AI Technical Lead

**Estimated time:** 14–18 hours

**Prerequisites:** Courses 07–10, 15, 17, 20–21, and 24–26

**Case study:** Northstar Mutual — AI-2605, a multi-repository document-classification and review-routing change

**Practical stack:** Python, pytest, Hypothesis, Git, SQLite, JSON Schema, contract testing, GitHub Actions, deterministic AI evaluation fixtures, mutation testing, failure injection, and authenticated evidence

## Course thesis

A coding agent may propose tests and use them for feedback, but credible quality evidence must independently execute the exact multi-repository implementation against protected requirements, oracles, contracts, failure states, and evaluation populations—and must never become its own merge or release authority.

## Learning objectives

By the end, you should be able to:

1. Separate candidate tests, independent verification, evaluation, and release authorization.
2. Derive a risk-based test portfolio from requirements, acceptance criteria, invariants, and non-functional requirements.
3. Design oracles that do not merely restate an agent's implementation.
4. Combine example, property, metamorphic, contract, integration, security, concurrency, recovery, and evaluation evidence.
5. Use mutation testing to measure whether a suite detects specified defects rather than counting tests.
6. Inject timeouts, duplicate delivery, stale approvals, and other realistic failure modes.
7. Detect stale, forged, wrong-subject, flaky, and candidate-only evidence.
8. Bind evidence to every participating Git commit plus contract, oracle, dataset, specification, suite, policy, producer, environment, and validity revisions.
9. Report metric populations, numerators, denominators, exclusions, and claim boundaries.
10. Compare probabilistic model versions using explicit populations, per-class metrics, protected slices, unsupported-claim rates, and holdouts.
11. Select risk-adaptive tests while treating unknown impact as uncertainty rather than no impact.
12. Produce a quality decision that stops at `READY_FOR_INTEGRATION_REVIEW` and never replaces protected delivery governance.

## Success criteria

You are complete when you can explain the oracle problem; map QI-001 through QI-005 to independent obligations; execute the Git-backed three-service fixture; diagnose tenant, authority, concurrency, provenance, evaluation, and evidence-integrity failures; compare model versions without hiding protected regressions; and defend why `CONFORMANT` is not delivery authorization.

## Non-goals

This course does not claim that a passing suite proves defect-free software, that one coverage percentage is a universal quality score, that a checked-in “protected” dataset has production-grade secrecy, that deterministic fixtures measure production model quality, or that agents may approve their own changes.

## Run the course

From the repository root:

```bash
python3 curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/lab.py
python3 -m unittest tests.test_course_27 -v
```

The reference path uses only Python's standard library and Git. To run the optional pytest/Hypothesis expansion:

```bash
python3 -m pip install -r curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/optional-tools.txt
python3 -m pytest curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/tests -q
```

Then open the guided [testing-and-quality notebook](northstar-quality-control/testing_quality.ipynb) and use the [lab guide](northstar-quality-control/README.md) for failure experiments and the staff workshop.

---

# Part I — Quality is a claim supported by evidence

## 1. Why agent-generated tests change the trust model

Agents can create broad suites quickly. That improves feedback speed, but volume is not independence. The same model can write implementation and tests from the same misunderstanding, copy an incorrect example into an oracle, assert only the happy path, or optimize for a visible coverage threshold.

The core boundary is:

```text
coding agent ── proposes code + candidate tests
                       │ diagnostic feedback
                       ▼
trusted change observer ── exact commits + contracts + oracles + dataset
                       │
independent harness ── behavior + properties + contracts + evaluation
                       │ signed evidence
                       ▼
quality control plane ── typed decision + findings + limitations
                       │
protected release workflow ── separate authorization
```

Candidate tests remain valuable. They accelerate development and prevent local regressions. They are not, by themselves, an independent attestation that the candidate satisfies the governing specification.

## 2. Four different questions

| Question | Typical evidence | Owner |
|---|---|---|
| Does this function behave as its local contract states? | Unit/property tests | Delivery team |
| Does the change satisfy authoritative requirements and boundaries? | Independent acceptance, contract, negative tests | Quality/product/control owners |
| Does the AI component perform acceptably on an approved population? | Versioned evaluation dataset and metrics | AI quality/domain owner |
| May this exact artifact be released now? | Current cross-domain evidence and approval | Protected release workflow |

Collapsing these questions creates false confidence. A model-quality evaluation cannot prove authorization. A unit suite cannot prove distributed recovery. A release approval cannot repair a weak oracle.

## 3. Quality model and requirement hierarchy

Quality begins before test code. Course 07 supplied acceptance criteria and invariants; Course 08 supplied measurable non-functional requirements; Course 09 reviewed specification quality. Course 27 converts those durable claims into an evidence portfolio.

```text
business outcome
  ├─ functional requirement
  │    ├─ acceptance scenario
  │    ├─ invariant
  │    └─ negative behavior
  ├─ non-functional requirement
  │    ├─ population + load
  │    ├─ threshold + window
  │    └─ measurement method
  └─ governance constraint
       ├─ authority boundary
       ├─ evidence producer
       └─ release disposition
```

A test should trace to one or more claims. A claim should identify the kinds of evidence needed for its risk, not merely point to a filename.

### AI-2605 protected invariants

| ID | Invariant | Consequence if violated |
|---|---|---|
| `QI-001` | Ambiguous classifications require authorized human review regardless of confidence | Unauthorized automation |
| `QI-002` | One tenant cannot access another tenant's documents or review state | Confidentiality breach |
| `QI-003` | AI proposals cannot mutate authoritative underwriting state | Loss of business control |
| `QI-004` | Retries and concurrent duplicates create at most one effect | Data inconsistency |
| `QI-005` | Every proposal preserves evidence and model provenance | Unverifiable decision |

The owner-controlled [verification obligations](northstar-quality-control/requirements/verification-obligations.json) convert each invariant into a population, evidence kinds, oracle owner, and revision. This is the layer an implementation agent cannot silently rewrite.

---

# Part II — The oracle problem

## 4. A test is only as strong as its expected result

The oracle decides whether observed behavior is correct. Weak oracle patterns include:

- copying current output into a snapshot and treating it as truth;
- asserting that no exception occurred;
- comparing two implementations that share the same defect;
- using model confidence as the expected business outcome;
- asking the same model to judge the answer it generated; and
- encoding an implementation detail rather than the requirement.

Northstar accepts three oracle sources in the teaching control plane:

1. **Approved specification** — exact behavior, invariant, or prohibited outcome.
2. **Independent reference** — a simpler, separately implemented function or property.
3. **Versioned contract** — schema, protocol, authorization, or compatibility contract.

Schema validity is necessary for structured results, but does not establish semantic correctness, authority, freshness, or safety.

## 5. From requirement to evidence obligation

For each requirement, record:

```yaml
requirement_id: REQ-QUALITY-002
risk: critical
claim: only an authorized underwriter persists authoritative classification
required_evidence:
  - contract
  - integration
  - negative
oracle:
  source: authorization-contract@4
  owner: identity-platform
failure_disposition: BLOCKED
```

Critical obligations should include a prohibited-path test. A positive test that proves an authorized user succeeds says nothing about whether an unauthorized agent is rejected.

## 6. Independence is a gradient

Independence can apply to author, tool, model, dataset, oracle, execution environment, and approval. It is rarely absolute.

| Arrangement | Useful for | Limitation |
|---|---|---|
| Same agent writes code and tests | Fast feedback | Correlated misunderstanding |
| Different agent, same prompt/context | Review breadth | Shared source and model bias |
| Independent harness, candidate-authored oracle | Reproducibility | Oracle may still be weak |
| Independent oracle and harness | Release-quality evidence | Higher cost and ownership needs |
| Runtime observation | Actual operating behavior | Later feedback; requires telemetry and safe rollout |

The right design is risk-proportionate. A documentation typo does not need dual independent implementations. An authorization boundary does.

---

# Part III — Build a layered test portfolio

## 7. Test kinds answer different questions

| Kind | Best signal | Common blind spot |
|---|---|---|
| Unit | Local branch and transformation | Integration assumptions |
| Property-based | Invariants across generated inputs | Incorrect property |
| Contract | Producer/consumer compatibility | Business workflow |
| Integration | Real component interaction | Rare failures |
| System/end-to-end | User-visible workflow | Slow diagnosis and sparse state space |
| Negative/security | Prohibited actions and hostile input | Unknown attacks |
| Failure/recovery | Safe behavior under dependency faults | Production topology gaps |
| Evaluation | Statistical AI behavior on a population | Authority and side effects |
| Runtime verification | Deployed behavior and SLOs | Pre-release defects |

The “testing pyramid” is a cost heuristic, not a law. Distributed and agentic systems often need more contract, integration, simulation, and runtime evidence than a simple deterministic library.

## 8. Property and metamorphic testing

Example-based tests choose inputs and expected outputs. Property-based tests generate inputs to exercise invariants. Useful properties for classification proposals include:

- unsupported document types never become authoritative classifications;
- repeating the same logical operation does not create duplicate state;
- adding irrelevant whitespace does not change a normalized classification;
- confidence ordering does not bypass authorization; and
- equivalent representations preserve a result.

Metamorphic testing is valuable when exact outputs are expensive to enumerate. It defines how outputs should relate when inputs change. A metamorphic relation is still an oracle and must be justified by the specification.

The credential-free lab enumerates all 101 two-decimal confidence values and verifies three low/high confidence transformations. The optional Hypothesis test expands that domain with generated floating-point inputs. Hypothesis can also generate operation sequences with rule-based state machines; that is useful when a failure depends on several review-state transitions rather than one value. Generation and shrinking improve discovery and diagnosis, but they do not make a property authoritative.

## 9. Contract and compatibility testing

Contract evidence must name producer, consumer, schema/protocol revision, and compatibility direction. Passing a provider test against a mock does not prove the deployed consumer uses that contract. Multi-repository delivery from Courses 20–21 therefore binds compatibility evidence to an exact revision set.

Course 27 creates isolated `ai-service`, `review-service`, and `underwriting-api` repositories, makes reproducible commits, imports code from those committed files, and records the three full SHAs. The harness validates the classification and review-state JSON Schemas and executes cross-service authority behavior. A contract digest without a matching consumer revision remains incomplete evidence.

## 10. AI evaluation is not ordinary unit testing

AI components can require population-based evaluation:

```text
approved dataset revision
  → exact system configuration
  → per-case outputs and traces
  → deterministic or human-reviewed scoring
  → slice metrics and safety violations
  → uncertainty and limitations
```

Record model, prompt, retrieval, tool, policy, dataset, and scorer revisions as applicable. Separate:

- component quality from end-to-end workflow quality;
- average performance from critical slice performance;
- blocked unsafe attempts from actual forbidden outcomes;
- deterministic rule checks from subjective rubric scores; and
- synthetic fixture accuracy from production reliability.

Never expose private chain-of-thought. Use observable outputs, citations, tool calls, decisions, reason codes, latency, cost, and terminal state.

### The executable model comparison

The fixture compares `v1`, proposed `v2`, and an intentionally overfit candidate on versioned development and holdout JSONL records. `v2` improves holdout classification accuracy from 6/8 to 8/8, yet it is `BLOCKED`: one high-confidence ambiguous case bypasses review and one conflicting-evidence case cites unsupported evidence. The overfit candidate scores 8/8 on visible development cases but only 2/8 on the holdout.

These numbers describe sixteen synthetic records, not a production benchmark. Their purpose is to make the decision logic inspectable: aggregate improvement cannot compensate for a protected failure.

---

# Part IV — Test the tests

## 11. Mutation testing

Mutation testing makes small controlled changes and asks whether the suite detects them. Course 27 selects seven architecture-significant mutations:

- ignore ambiguity;
- remove the tenant filter;
- drop the idempotency key;
- accept expired approval;
- drop evidence references;
- allow the AI service to mutate authoritative state; and
- treat review-service outage as success.

A mutation score is:

```text
killed selected mutants / executed selected mutants
```

The denominator matters. Adding easy mutants can inflate a score. Silently excluding hard or equivalent mutants can do the same. The policy therefore owns the critical mutation set. A missing required mutation is insufficient evidence; a surviving critical mutant blocks.

Mutation testing does not prove the absence of other defects. It measures sensitivity to the selected fault model.

## 12. Stateful, concurrent, and failure testing

Happy-path tests rarely establish safe failure behavior. Inject failures at boundaries:

- timeout before an effect;
- timeout after an effect with unknown outcome;
- duplicate queue delivery;
- stale approval;
- partial dependency failure;
- cancellation;
- restart between durable transitions; and
- concurrent attempts using the same logical operation.

Assertions should cover state, effect count, retry class, idempotency key, approval consumption, audit evidence, and terminal outcome. “The request eventually succeeded” is too weak.

The Review Service fixture uses SQLite's `PRIMARY KEY` uniqueness and `BEGIN IMMEDIATE` transaction boundary. Two threads submit the same logical operation concurrently: one result is `APPLIED`, the other is `REPLAYED`, and one durable effect exists. Reusing the key with another payload returns `IDEMPOTENCY_CONFLICT`. The fault suite also proves that an interrupted pre-commit transaction leaves zero effects, expired and revoked approvals are rejected, and a review-service outage enters `REVIEW_UNAVAILABLE_SAFE_HOLD`.

SQLite is a teaching boundary, not proof of behavior in another database. A production implementation must re-run the concurrency and rollback obligations against the actual persistence engine and isolation configuration.

## 13. Differential and model-based testing

Differential testing compares independent implementations or versions. Model-based testing generates operations from an explicit state machine and checks observed transitions. Both are powerful only when their independence and state model are credible.

For an agent workflow, a state model can prohibit transitions such as:

```text
PROPOSED ──agent text──> PERSISTED       # invalid
PROPOSED ──trusted approval──> APPROVED  # allowed
APPROVED ──atomic execution──> PERSISTED # allowed
```

---

# Part V — Evidence integrity

## 14. Exact-subject binding

Quality evidence becomes stale when any decision-relevant subject changes. Bind it to:

```text
ai-service commit
+ review-service commit
+ underwriting-api commit
+ implementation/revision-set digest
+ contract digest
+ protected-oracle digest
+ holdout-dataset digest
+ specification revision
+ quality policy revision
+ suite revision
+ evidence producer
+ issued/expiry time
+ case, mutation, and fault populations
```

An evidence ID alone proves nothing. The record must exist, authenticate, match the exact subject, and support the claim.

## 15. Flaky tests

A flaky test passes and fails for the same subject. Retries can help diagnosis but cannot turn mixed outcomes into positive evidence. Course 27 returns `REVIEW_REQUIRED`, preserves the missing obligation, and requires the owner to repair or replace the test.

Common sources include order dependence, shared mutable state, timing assumptions, randomness without a recorded seed, network dependencies, uncontrolled clocks, resource leaks, and concurrency.

Quarantine should be visible, owned, time-bounded, and risk-aware. Silent retry-until-green corrupts the signal.

## 16. Metric integrity

Every quality metric should name:

- population and revision;
- numerator and denominator;
- unit and direction;
- slices and aggregation;
- exclusions and missing data;
- decision threshold and owner; and
- the claim the metric can and cannot support.

Code coverage measures execution, not assertion strength. Test count measures inventory, not behavioral breadth. Pass rate can improve when difficult tests are deleted. Quality dashboards should make these failure modes visible.

---

# Part VI — Quality control plane

## 17. Decision vocabulary

Course 27 uses six explicit states:

| Decision | Meaning |
|---|---|
| `CONFORMANT` | Registered obligations have current independent passing evidence |
| `BLOCKED` | Evidence establishes a prohibited or unsafe outcome |
| `INSUFFICIENT_EVIDENCE` | Required proof is absent, forged, malformed, or untrusted |
| `REVIEW_REQUIRED` | Evidence is nondeterministic or needs accountable resolution |
| `STALE_EVIDENCE` | Authenticated evidence covers an older subject, suite, policy, or validity interval |
| `CONFORMANT_WITH_EXCEPTION` | A separately authorized, applicable, current exception modifies the disposition |

These states prevent “unknown” from becoming “pass.” The reference report always sets merge, deployment, activation, and release authorization to `false`; `CONFORMANT_WITH_EXCEPTION` is part of the contract but is not exercised by the clean reference path.

## 18. Worked Northstar scenario: AI-2605

Northstar proposes a revised classifier and review router. Repository-local tests pass and aggregate fixture accuracy improves. The approved specification still says the model may propose; only an authorized underwriter may persist the authoritative result, ambiguity always requires review, and evidence must remain supported.

The independent portfolio includes:

1. example, property, and metamorphic evidence for ambiguous outcomes;
2. tenant and authorization contract/integration tests;
3. negative tests for cross-tenant access and unauthorized persistence;
4. transactional concurrency, failure, and recovery tests;
5. seven policy-selected critical mutations;
6. six safe-state failure experiments;
7. v1/v2/overfit evaluation on development and protected holdout populations; and
8. evidence binding to exact commits, contracts, oracles, dataset, suite, policy, producer, and time.

The corrected reference implementation is `CONFORMANT` and stops at `READY_FOR_INTEGRATION_REVIEW`. Proposed `v2` is blocked despite higher classification accuracy. If a protected test is deleted, the decision becomes insufficient; if it is flaky, it requires review; if any participating commit changes after execution, evidence is stale. Course 24 still owns the protected release decision.

## 19. Risk-adaptive selection without boundary erosion

The [test selector](northstar-quality-control/quality_app/test_selector.py) unions impact-derived tests with policy-mandated boundary checks:

| Change category | Minimum additional strategy |
|---|---|
| Documentation | Link, example, and documentation validation |
| Local deterministic bug | Red-green regression, unit, and affected negative tests |
| Shared API | Contract and affected-consumer integration tests |
| Database | Migration, rollback, concurrency, and integrity tests |
| Authorization | Protected security, negative, and integration tests |
| AI model or prompt | Versioned evaluation, protected slices, and deterministic safety invariants |
| Cross-repository | Exact-revision contract, integration, and failure tests |
| Critical workflow | Failure, recovery, and operational-readiness evidence |

If the dependency graph cannot resolve impact, the selector returns `IMPACT_REVIEW_REQUIRED` while retaining mandatory protected-boundary tests. Unknown impact is not no impact, and an implementation agent cannot reduce the suite merely by labelling its own change low risk.

## 20. When not to use the full process

Use a lightweight path for low-risk, reversible changes with stable deterministic behavior and no protected boundary. Do not require an enterprise evidence bundle for every copy edit.

Use the full process when changes affect authorization, money, regulated data, external communications, autonomous side effects, shared contracts, distributed recovery, AI safety, or other consequential behavior.

---

# Part VII — Technology landscape

## 21. Select tools by evidence need

| Need | Examples | Selection questions |
|---|---|---|
| Unit/integration execution | pytest, unittest, JUnit, Vitest | Isolation, fixtures, parallel behavior, reporting |
| Property testing | Hypothesis, jqwik, fast-check | Generator quality, shrinking, reproducibility |
| Mutation testing | mutmut, PIT, Stryker | Language support, incremental cost, mutant control |
| Contract testing | Pact, schema validators, provider verification | Broker trust, revision binding, compatibility direction |
| Revision identity | Git commit objects, signed tags, build provenance | Full revision set, dirty state, source authenticity |
| Transactional concurrency | SQLite fixture; production database integration | Uniqueness, isolation, retry, rollback, engine parity |
| Fuzzing | libFuzzer, AFL++, language-native fuzzers | Harness quality, corpus, sanitizer support |
| Failure injection | Toxiproxy, service meshes, cloud fault tools | Blast radius, observability, cleanup |
| AI evaluation | task-specific harnesses and versioned datasets | Dataset authority, scorer validity, slice analysis |
| CI evidence | GitHub Actions, protected runners, artifact attestations | Workload identity, immutability, permissions, retention |

Tools do not solve authority or oracle design. A framework can execute an assertion; it cannot decide which organizational source owns the expected behavior.

## 22. Established, emerging, and open problems

Established practice includes layered testing, independent review, property and contract testing, fuzzing, mutation testing, failure injection, revision-bound CI, and protected evidence. GitHub artifact attestations can establish where and how a build was produced; they complement rather than replace behavioral verification.

Emerging practice includes agent-generated test portfolios, semantic trace validation, automated invariant extraction, and evaluation-aware change impact. These can accelerate discovery, but generated tests and judges still require oracle governance and independent validation.

Open problems include measuring semantic coverage, controlling correlated model/judge errors, selecting representative long-tail failure populations, evaluating nondeterministic multi-agent behavior, and updating tests without laundering specification drift.

---

# Part VIII — Production upgrade and exercises

## 23. Production upgrade path

| Teaching fixture | Production upgrade |
|---|---|
| HMAC training keys | Workload identity, managed signing, rotation, revocation |
| Local JSON policy | Protected, versioned policy and test catalogs |
| Deterministic fixtures | Representative, approved, privacy-reviewed datasets |
| One process | Isolated workers, durable queues, resource budgets |
| Synthetic faults | Staging and carefully bounded production experiments |
| Simple expiry | Trusted time, retention, revocation, replay protection |
| Fixed critical mutants | Change-aware mutation selection with owner review |
| Local report | Immutable evidence store and release-system integration |
| Checked-in holdout | Access-controlled evaluation service with development/holdout separation and audit |
| SQLite concurrency fixture | Real database, queue, and transaction-isolation integration tests |
| Reproducible local Git commits | Verified source provenance and CI-issued artifact attestations |

Also add tenant isolation, secret handling, sandboxing, artifact provenance, test-data lifecycle, cost controls, flake ownership, observability, rollback, and disaster recovery.

## 24. Staff exercises

1. **Implementation:** add a new protected invariant and update the obligations, test selection, mutation portfolio, evidence, and traceability without granting the agent oracle authority.
2. **Diagnosis:** alter `IGNORE_AMBIGUITY`, inspect the minimal property/metamorphic counterexample, and explain why a test name would not be proof.
3. **Concurrency:** change the Review Service uniqueness strategy, run two identical and two conflicting concurrent requests, and explain each durable state.
4. **Evaluation:** create a third model whose average accuracy rises while rare-document recall falls; design an owner-approved disposition.
5. **Contamination:** add another visible-case shortcut and show how the holdout and changed-document population expose it.
6. **Architecture judgment:** decide which evidence a documentation-only change can skip and which protected checks a shared-contract change must retain.
7. **Failure:** inject an unknown-outcome timeout and specify reconciliation before retry.
8. **Metric integrity:** find a gameable numerator, denominator, exclusion, or slice aggregation and redesign it.
9. **Staff workshop:** complete the [quality strategy](northstar-quality-control/workshop/starter/quality-strategy.json) and compare it with the [reference](northstar-quality-control/workshop/reference/quality-strategy.json).

## 25. Review questions

- Why can candidate tests be useful without being independent evidence?
- What makes an oracle authoritative for one claim?
- When does a surviving mutant block rather than trigger review?
- Why do identical retries and conflicting idempotency-key reuse require different outcomes?
- Why can a model with higher aggregate accuracy still be blocked?
- What does a development/holdout gap suggest, and what does it not prove?
- Why is retry-until-green not a flake policy?
- Which subject changes invalidate quality evidence?
- Why can 100% code coverage coexist with a critical authorization defect?
- What does `CONFORMANT` explicitly not authorize?

## References

- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- [NIST SP 800-218A Generative AI SSDF Community Profile](https://csrc.nist.gov/pubs/sp/800/218/a/final)
- [pytest documentation: flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/en/latest/)
- [Hypothesis documentation: stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
- [Pact contract testing documentation](https://docs.pact.io/)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [SQLite ON CONFLICT behavior](https://www.sqlite.org/lang_conflict.html)
- [Git documentation: revision selection](https://git-scm.com/book/en/v2/Git-Tools-Revision-Selection)
- [GitHub Actions: artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [LLVM libFuzzer documentation](https://llvm.org/docs/LibFuzzer.html)
- [Google Testing Blog: Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)
