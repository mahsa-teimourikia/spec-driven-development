# Course 27 — Testing and Quality for Agentic Spec-Driven Development

> Enterprise Spec-Driven Development · Part V: Enterprise Controls · Course 27 of 38

**Level:** Advanced / Staff Engineer, Quality Architect, Platform Engineer, and AI Technical Lead

**Estimated time:** 10–14 hours

**Prerequisites:** Courses 07–10, 17–19, and 24–26

**Case study:** Northstar Mutual — independent quality evidence for an agent-generated document-classification change

**Practical stack:** Python, JSON Schema, requirement traceability, property and contract testing concepts, mutation testing, failure injection, signed evidence, and CI gates

## Course thesis

A coding agent may propose tests and use them for feedback, but credible release-quality evidence must be independently produced, traceable to an authoritative specification, bound to the exact change, capable of detecting specified failures, and interpreted within explicit limits.

## Learning objectives

By the end, you should be able to:

1. Separate candidate tests, independent verification, evaluation, and release authorization.
2. Derive a risk-based test portfolio from requirements, acceptance criteria, invariants, and non-functional requirements.
3. Design oracles that do not merely restate an agent's implementation.
4. Combine unit, property, contract, integration, system, negative, recovery, and evaluation evidence.
5. Use mutation testing to measure whether a suite detects specified defects rather than counting tests.
6. Inject timeouts, duplicate delivery, stale approvals, and other realistic failure modes.
7. Detect stale, forged, wrong-subject, flaky, and candidate-only evidence.
8. Bind evidence to an implementation digest, specification revision, suite revision, policy revision, producer, and validity window.
9. Report metric populations, numerators, denominators, exclusions, and claim boundaries.
10. Produce a quality decision that supports—but never replaces—protected release governance.

## Success criteria

You are complete when you can explain the oracle problem, map risks to test kinds, run the deterministic control plane, diagnose at least three evidence failures, design a critical mutation set, and defend why a green quality report is not release authorization.

## Non-goals

This course does not claim that a passing suite proves defect-free software, that one coverage percentage is a universal quality score, that deterministic fixtures measure production model quality, or that agents may approve their own changes.

## Run the course

From the repository root:

```bash
python3 curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/lab.py
python3 -m unittest tests.test_course_27 -v
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
trusted change observer ── exact implementation/specification subject
                       │
independent harness ── tests + mutations + failure experiments
                       │ signed evidence
                       ▼
quality control plane ── typed decision + limitations
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

## 9. Contract and compatibility testing

Contract evidence must name producer, consumer, schema/protocol revision, and compatibility direction. Passing a provider test against a mock does not prove the deployed consumer uses that contract. Multi-repository delivery from Courses 20–21 therefore binds compatibility evidence to an exact revision set.

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

---

# Part IV — Test the tests

## 11. Mutation testing

Mutation testing makes small controlled changes and asks whether the suite detects them. Course 27 selects four architecture-significant mutations:

- remove authorization;
- accept unsupported input;
- drop the idempotency key; and
- treat timeout as success.

A mutation score is:

```text
killed selected mutants / executed selected mutants
```

The denominator matters. Adding easy mutants can inflate a score. Silently excluding hard or equivalent mutants can do the same. The policy therefore owns the critical mutation set. A missing required mutation is insufficient evidence; a surviving critical mutant blocks.

Mutation testing does not prove the absence of other defects. It measures sensitivity to the selected fault model.

## 12. Failure injection and recovery

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
repository revision
+ implementation digest
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

Course 27 uses four states:

| Decision | Meaning |
|---|---|
| `QUALITY_EVIDENCE_ACCEPTED` | Registered obligations have current independent passing evidence |
| `BLOCKED` | Evidence establishes a prohibited or unsafe outcome |
| `INSUFFICIENT_EVIDENCE` | Required proof is absent, stale, forged, mismatched, or untrusted |
| `REVIEW_REQUIRED` | Evidence is nondeterministic or needs accountable resolution |

These states prevent “unknown” from becoming “pass.” The report always sets `release_authorized=false`.

## 18. Worked Northstar scenario

An agent proposes automatic persistence when classification confidence is high. The approved specification says the model may propose; only an authorized underwriter may persist the authoritative result.

The independent portfolio includes:

1. unit and property evidence for unsupported and ambiguous outcomes;
2. authorization contract and integration tests;
3. negative tests for unauthorized persistence;
4. failure/recovery tests for duplicates and timeouts;
5. four policy-selected mutations; and
6. stale-approval failure injection.

If the authorization-removal mutant survives, the change blocks even if every existing test is green. If the test is flaky, it cannot satisfy the obligation. If the report is green, Course 24 still performs the protected release decision.

## 19. When not to use the full process

Use a lightweight path for low-risk, reversible changes with stable deterministic behavior and no protected boundary. Do not require an enterprise evidence bundle for every copy edit.

Use the full process when changes affect authorization, money, regulated data, external communications, autonomous side effects, shared contracts, distributed recovery, AI safety, or other consequential behavior.

---

# Part VII — Technology landscape

## 20. Select tools by evidence need

| Need | Examples | Selection questions |
|---|---|---|
| Unit/integration execution | pytest, unittest, JUnit, Vitest | Isolation, fixtures, parallel behavior, reporting |
| Property testing | Hypothesis, jqwik, fast-check | Generator quality, shrinking, reproducibility |
| Mutation testing | mutmut, PIT, Stryker | Language support, incremental cost, mutant control |
| Contract testing | Pact, schema validators, provider verification | Broker trust, revision binding, compatibility direction |
| Fuzzing | libFuzzer, AFL++, language-native fuzzers | Harness quality, corpus, sanitizer support |
| Failure injection | Toxiproxy, service meshes, cloud fault tools | Blast radius, observability, cleanup |
| AI evaluation | task-specific harnesses and versioned datasets | Dataset authority, scorer validity, slice analysis |

Tools do not solve authority or oracle design. A framework can execute an assertion; it cannot decide which organizational source owns the expected behavior.

## 21. Established, emerging, and open problems

Established practice includes layered testing, independent review, property and contract testing, fuzzing, mutation testing, failure injection, and protected CI evidence.

Emerging practice includes agent-generated test portfolios, semantic trace validation, automated invariant extraction, and evaluation-aware change impact. These can accelerate discovery, but generated tests and judges still require oracle governance and independent validation.

Open problems include measuring semantic coverage, controlling correlated model/judge errors, selecting representative long-tail failure populations, evaluating nondeterministic multi-agent behavior, and updating tests without laundering specification drift.

---

# Part VIII — Production upgrade and exercises

## 22. Production upgrade path

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

Also add tenant isolation, secret handling, sandboxing, artifact provenance, test-data lifecycle, cost controls, flake ownership, observability, rollback, and disaster recovery.

## 23. Staff exercises

1. Identify the weakest oracle in an existing suite and replace it with a specification, contract, property, or independent reference.
2. Design three mutations that would expose authority laundering or unsafe fallback.
3. Inject an unknown-outcome timeout and specify reconciliation before retry.
4. Create a traceability matrix from five SHALL requirements to positive, negative, and failure evidence.
5. Find a metric with a gameable denominator and redesign it.
6. Decide which evidence a documentation-only change can safely skip and record the rationale.
7. Complete the [quality strategy workshop](northstar-quality-control/workshop/starter/quality-strategy.json) and compare it with the [reference](northstar-quality-control/workshop/reference/quality-strategy.json).

## 24. Review questions

- Why can candidate tests be useful without being independent evidence?
- What makes an oracle authoritative for one claim?
- When does a surviving mutant block rather than trigger review?
- Why is retry-until-green not a flake policy?
- Which subject changes invalidate quality evidence?
- Why can 100% code coverage coexist with a critical authorization defect?
- What does `QUALITY_EVIDENCE_ACCEPTED` explicitly not authorize?

## References

- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- [NIST SP 800-218A Generative AI SSDF Community Profile](https://csrc.nist.gov/pubs/sp/800/218/a/final)
- [pytest documentation: flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/en/latest/)
- [Pact contract testing documentation](https://docs.pact.io/)
- [LLVM libFuzzer documentation](https://llvm.org/docs/LibFuzzer.html)
- [Google Testing Blog: Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)

