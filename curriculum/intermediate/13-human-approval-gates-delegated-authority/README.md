# Course 23 — Human Approval Gates and Delegated Authority in Agentic SDD

> Enterprise Spec-Driven Development · Part IV: Agentic PDLC · Course 23 of 38

**Level:** Advanced intermediate / staff AI scientist

**Prerequisites:** Courses 10, 16, 17, and 20–22

**Case study:** Northstar Mutual · governed deployment of an AI underwriting assistant

**Practical stack:** Python, SQLite, OpenSpec, JSON policy, illustrative OPA/Rego, notebooks, adversarial tests

## Course thesis

A human click is not an enterprise control. A protected action may proceed only when a trusted enforcement point can prove that authenticated principals with current, resource-scoped authority approved the exact action subject under the applicable policy, that separation-of-duties obligations are satisfied, and that each approval is still valid and atomically consumed.

## Why this course matters

Course 22 separated implementation review, merge eligibility, deployment, and release. This course makes the human decision boundary executable. Agents can ask for approval, summarize evidence, and propose a course of action. They cannot declare the approver's identity, mint authority, widen a delegation, change the approved subject, or consume the same authorization twice.

Weak implementations often reduce approval to a Boolean:

```json
{"approved": true}
```

That record cannot answer who approved, what they approved, which authority they exercised, which policy applied, whether the artifact changed, whether the decision expired, or whether it was already used. The result is ceremony without dependable authorization.

## Learning objectives

By the end, you should be able to:

1. Distinguish human review, approval, authorization, accountability, and execution.
2. Model a protected decision as a typed, exact-subject authorization.
3. Choose risk-adaptive gates without forcing people to approve every agent action.
4. Resolve identity and authority from trusted systems rather than agent-supplied claims.
5. Enforce requester, author, approver, and executor separation where policy requires it.
6. Bind approval receipts to artifact, specification, policy, resource, action, and environment.
7. Attenuate delegated authority by action, resource, risk, time, and redelegation rights.
8. Enforce expiry, revocation, invalidation, and single-use consumption.
9. Design emergency authorization for reversible containment rather than unrestricted bypass.
10. Produce reconstructable, tamper-evident approval evidence.
11. Test the control with negative, mutation, concurrency, and recovery scenarios.
12. Identify the upgrades required before a teaching control plane becomes production infrastructure.

## Start here

Run the credential-free reference lab from the repository root:

```bash
python3 curriculum/intermediate/13-human-approval-gates-delegated-authority/northstar-approval-control/lab.py
python3 -m unittest tests.test_course_23 -v
```

Then use the guided [notebook](northstar-approval-control/human_approval_gates.ipynb), inspect the [Northstar control plane](northstar-approval-control/README.md), and complete the learner decisions in [`workshop/starter/approval-design.json`](northstar-approval-control/workshop/starter/approval-design.json).

The fixture uses Python's standard library, local temporary databases, and synthetic identities. It needs no credentials and performs no production action.

---

## Part I — Understanding human authority

### 1. Human-in-the-loop is not a complete governance model

“Ask a human” leaves the important questions unanswered:

- Which human?
- Acting in which organizational role?
- Authorized over which resource and decision?
- Reviewing which exact revision?
- Using which evidence?
- Until when is the decision valid?
- Can it be revoked or reused?
- Which system enforces the result?

A chat response or issue comment can support collaboration. It is not automatically authorization. The control plane must authenticate the person, resolve their current grant independently, and bind the decision to a protected subject.

### 2. Approval is a typed decision

Treat an approval as a tuple:

```text
approval = (
  principal, role, decision_type, subject_digest,
  authority_source, policy_revision,
  issued_at, expires_at, usage, state
)
```

The type matters. A security exception does not imply architecture approval. Merge approval does not imply production release. Model approval may not authorize a data-retention exception. An enterprise vocabulary should name protected decisions and the roles permitted to make each one.

The agent is a proposer and evidence producer. The trusted service is the verifier and state-transition authority.

---

## Part II — Risk-tiered approval gates

### 3. Do not approve every agent action

Universal manual approval creates queues, fatigue, and low-signal clicking. It can make the system less safe because consequential decisions become visually indistinguishable from routine ones.

Automate bounded, reversible, well-tested work. Add human authority where the residual risk, irreversibility, protected data, customer effect, policy exception, or production blast radius justifies it.

### 4. Risk-adaptive approval matrix

| Risk | Example | Evidence | Gate |
| --- | --- | --- | --- |
| Low | local documentation or generated fixture | automated checks | no manual approval |
| Moderate | staging deployment or reversible shared change | tests, scope, rollback | one scoped authority |
| Consequential | production model behavior or regulated workflow | conformance, security, rollout, observability | dual control |
| Critical | irreversible migration or safety-critical operation | independent validation and recovery proof | specialized authorities or prohibit automation |

Risk is not a label supplied by the coding agent. Derive it from authoritative attributes and policy, and fail closed when the policy cannot resolve the case.

### 5. A gate is a state transition

```text
PROPOSED → EVIDENCE_READY → AWAITING_AUTHORITY → AUTHORIZED
                                                  │
                                      ┌───────────┴───────────┐
                                      ▼                       ▼
                                  CONSUMED                  REVOKED
```

Rejection and expiry are terminal for the receipt, not necessarily the change. A revised subject creates a new authorization problem. Editing the old record must not make the new subject appear approved.

---

## Part III — Approval receipts and exact-subject binding

### 6. What is an approval receipt?

A receipt is a durable authorization fact issued by a trusted service after it verifies identity, role, authority scope, policy, evidence, and separation of duties. It is a reference, not a bearer string whose contents callers may invent.

The reference implementation stores receipts in SQLite and accepts only receipt identifiers at the protected execution boundary. Every fact is re-resolved from trusted state.

### 7. Exact binding prevents approval drift

The course subject digest covers:

```text
change ID + action + resource + environment + artifact digest
+ specification digest + policy revision + risk tier + incident ID
```

If any material field changes, the digest changes. An approval for artifact A cannot authorize artifact B. A production approval cannot be replayed against staging or another service. An emergency receipt bound to one incident cannot authorize unrelated work.

Do not bind only a mutable branch, tag, ticket, or deployment name. Resolve immutable artifacts and versioned policy inputs.

### 8. Verify at the protected action boundary

The executor must verify immediately before the side effect:

1. the request and receipts exist in trusted storage;
2. the requested action subject exactly matches the approved subject;
3. the policy revision is current for that decision mode;
4. all required roles are present;
5. approvers are distinct when dual control applies;
6. each principal still has current direct or delegated authority;
7. receipts are approved, unexpired, unrevoked, and unused; and
8. consumption and operation registration occur atomically.

A UI check is advisory if the backend can execute without repeating these checks.

---

## Part IV — Separation of duties and delegated authority

### 9. Separation of duties is decision-specific

The objective is not maximum separation. It is to prevent a single actor from controlling incompatible steps in a consequential decision. Typical constraints include:

- the requester cannot approve the request;
- the implementation author cannot independently approve its implementation;
- two required roles must be exercised by two principals;
- a policy administrator should not unilaterally alter audit evidence; and
- an executor cannot silently invent approval state.

NIST SP 800-53 AC-5 describes documenting separated duties and defining access authorizations that support them. Your policy must turn that principle into decision-specific constraints.

### 10. Model the constraint, not just a group name

```json
{
  "decision": "deploy",
  "risk": "CONSEQUENTIAL",
  "required_roles": ["release_authority", "ai_governance_owner"],
  "distinct_principals": true,
  "forbidden_relations": ["requester", "implementation_author"]
}
```

Membership in a team may help resolve a grant, but a team name alone does not prove resource scope, current employment, time bounds, or the decision being exercised.

### 11. Delegation is derived authority

Delegation transfers a bounded subset of an existing grant. The parent remains the upper bound:

```text
child.actions      ⊆ parent.actions
child.resources    ⊆ parent.resources
child.environments ⊆ parent.environments
child.max_risk     ≤ parent.max_risk
child.time_window  ⊆ parent.time_window
```

The reference system prohibits redelegation. A production design may allow it, but every link must preserve attenuation, depth limits, provenance, revocation, and current-parent validation.

### 12. Delegation grant example

```json
{
  "delegation_id": "DELEGATION-VALID",
  "parent_grant_id": "GRANT-SECURITY-EXCEPTION",
  "delegator": "security-director-2",
  "delegate": "security-lead-9",
  "role": "security_exception_approver",
  "actions": ["approve_low_risk_exception"],
  "resources": ["underwriting-platform"],
  "max_risk": "LOW",
  "may_redelegate": false
}
```

The delegate receives neither the director's title nor unrelated authority. The grant authorizes one role over one resource class for a bounded period.

### 13. Verify the complete delegation chain

At decision time and again at execution time, verify the parent exists, remains active, belongs to the delegator, permits delegation, covers the child scope, and has not expired. Parent revocation invalidates downstream authority even if a receipt was issued earlier.

This distinction is important: approval issuance records a decision; execution still depends on current authority when policy requires it.

---

## Part V — Lifecycle, revocation, and replay

### 14. Approvals are not permanent

Invalidate or re-evaluate approval when the artifact, specification, target resource, environment, risk, policy, evidence, authority, or incident context changes. Time alone can also invalidate it.

Long-lived, generic approvals are convenient precisely because they remove the protection the gate was meant to provide.

### 15. Approval state machine

```text
REQUESTED → APPROVED → CONSUMED
     │           ├──→ REVOKED
     │           └──→ EXPIRED
     └──────────────→ REJECTED
```

State transitions are append-audited. Consumers cannot move `REVOKED`, `EXPIRED`, or `CONSUMED` back to `APPROVED`.

### 16. Atomic single-use consumption

Checking `state == APPROVED` and updating later creates a time-of-check/time-of-use race. Two workers can both observe the same valid receipt.

The lab starts a SQLite `BEGIN IMMEDIATE` transaction, revalidates all receipts, marks them consumed with a conditional update, registers the operation, and commits. A two-worker test proves exactly one execution succeeds.

For an external deployment API, a local database transaction cannot make the remote side effect atomic. Production systems also need an idempotency key, durable outbox or workflow state, reconciliation, and explicit handling of “remote succeeded, local acknowledgement failed.”

---

## Part VI — Policy as code

### 17. Why make approval rules executable?

Policy as code makes rules versionable, reviewable, testable, and consistently evaluable. It also exposes unresolved combinations instead of letting each workflow invent an answer.

This lab uses [`approval-policy.json`](northstar-approval-control/policies/approval-policy.json) as the authoritative runtime input and includes an illustrative [`approval.rego`](northstar-approval-control/policies/approval.rego). A production program should choose and govern one authoritative evaluator to prevent policy drift.

### 18. Separate policy inputs from caller claims

Trusted inputs include authenticated principal identity, authority grants, protected-resource registry, current policy revision, incident state, and stored receipts. Untrusted inputs include agent summaries, proposed role labels, scenario expected outcomes, and receipt-like JSON sent by a caller.

The engine accepts references and resolves facts. It does not trust a caller to submit `"role": "release_authority"` as proof.

### 19. Policy decision is not enforcement

An OPA or JSON decision can say “allow,” but the protected service must still enforce it. Enforcement includes transactionality, exact-subject comparison, revocation checks, usage consumption, side-effect idempotency, and audit persistence.

OPA documents Rego as a declarative language for policy evaluation over structured data. That makes it useful for decision logic; it does not replace the stateful action boundary.

---

## Part VII — Emergency authorization and recovery

### 20. Emergency mode is not governance bypass

An incident changes objectives and latency, not the need for authority. Break-glass should be more observable and narrower than normal access, not a hidden administrator shortcut.

### 21. Normal versus emergency authorization

| Property | Normal deployment | Emergency containment |
| --- | --- | --- |
| Objective | deliver approved change | limit active harm |
| Subject | release artifact and environment | incident, resource, containment action |
| Typical gate | dual control | on-call scoped authority |
| Action set | governed deployment operations | pre-approved reversible containment |
| Evidence timing | before action | before action plus mandatory retrospective |

### 22. Break-glass authorization

The reference emergency policy requires an active SEV1 or SEV2 incident, an affected resource, a permitted containment action, an authenticated emergency responder, a short-lived receipt, and a versioned emergency policy.

No incident means no emergency mode. A SEV1 on the underwriting assistant cannot authorize a change to payments. Closing the incident invalidates later emergency requests.

### 23. Prefer reversible containment

Good emergency actions disable a risky feature, restore manual review, isolate traffic, reduce permissions, or roll back to a verified artifact. They should minimize irreversible data changes and broad configuration mutation.

Recovery is a separate authorized transition. “Disable AI classification” does not imply “deploy arbitrary replacement model.”

---

## Part VIII — Auditability and evidence

### 24. What must be reconstructable?

An auditor or incident reviewer should be able to determine:

- the exact subject and policy revision;
- requester, implementation author, approvers, roles, and authority sources;
- evidence available at decision time;
- delegation lineage and revocations;
- decision, denial, expiry, and consumption events;
- the executed operation and time; and
- emergency incident and retrospective obligations.

### 25. Approval evidence is a graph

```text
policy revision ─┐
resource record ─┼→ required roles ─→ authority grants ─→ receipts
subject digest ──┤                                      │
incident state ──┘                                      ▼
                                                protected operation
                                                        │
                                                        ▼
                                                  audit sequence
```

Saving only the final “approved” status destroys the relationships needed to explain why the action was permitted.

### 26. Tamper-evident is not tamper-proof

The lab hash-links each audit event to the previous event and proves that modifying an earlier reason code breaks chain verification. This detects a class of after-the-fact alteration. It does not prevent a privileged database operator from rewriting the entire chain.

Production evidence needs append controls, restricted administration, external anchoring or signed attestations where appropriate, retention policy, time integrity, monitoring, and independent recovery.

---

## Part IX — Northstar practical lab

### 27. Architecture

```text
agent or requester
  proposes change + receipt references
                │
                ▼
trusted approval application
  authenticates principal
  resolves policy, resource, incident, grants, delegation
  issues revision-bound receipts
                │
                ▼
protected executor
  re-resolves current facts
  atomically consumes receipts
  records one operation + audit evidence
```

### 28. Package map

| Path | Purpose |
| --- | --- |
| `approval_app/models.py` | typed action, authority, delegation, receipt result, and error contracts |
| `approval_app/control_plane.py` | trusted resolution, decision, consumption, and hash-linked audit boundary |
| `approval_app/simulation.py` | golden scenarios, adversarial evaluations, concurrency, and audit mutation |
| `policies/` | versioned normal, emergency, risk, separation, and illustrative Rego policy |
| `registry/` | synthetic authenticated sessions, direct grants, incidents, and protected resources |
| `scenarios/` | human-readable test intentions; never evaluator truth |
| `openspec/` | proposal, delta requirements, and completed tasks |
| `workshop/` | learner design and reference comparison |

### 29. Trusted approval decision

The production deployment requires `release_authority` and `ai_governance_owner`. The requester and implementation author cannot satisfy either approval. Both receipt records bind the same subject digest and are rechecked against current grants at execution.

### 30. Single-use authorization

The executor uses receipt identifiers, not caller-provided receipt bodies. It rejects unknown, mismatched, revoked, expired, consumed, policy-stale, or currently unauthorized records with stable reason codes.

---

## Part X — Failure injection and conformance

### 31. Golden scenarios

The conformance suite executes 12 required scenarios:

1. valid exact artifact;
2. changed artifact after approval;
3. expired receipt;
4. revoked receipt;
5. replayed receipt;
6. forged receipt reference;
7. authority for the wrong resource;
8. requester self-approval;
9. delegation scope expansion;
10. parent revocation after delegated approval;
11. two-worker concurrent consumption; and
12. valid incident-bound emergency containment.

Scenario labels are documentation. The control plane derives outcomes from trusted policy and registry state.

### 32. Mutation testing

Useful mutations change one protected dimension at a time: artifact digest, resource, environment, policy revision, incident, expiry, role, parent grant, or receipt state. The expected result is a stable fail-closed code, not a generic exception or silent fallback.

### 33. Concurrency experiment

The lab opens separate database connections from two worker threads. Both target the same request and receipt. The invariant is:

```text
successful executions = 1
registered operations = 1
losing result = APPROVAL_ALREADY_CONSUMED
```

Running the workers sequentially would test replay, not the race.

---

## Part XI — Enterprise operating model

### 34. Who owns the system?

| Capability | Accountable owner |
| --- | --- |
| protected-decision taxonomy | risk and business governance |
| identity and workforce status | identity platform |
| authority grants and delegation | resource owner with governance oversight |
| approval policy | security, architecture, AI governance, and delivery owners |
| enforcement service | platform engineering |
| audit retention and access | security/compliance |
| emergency action catalogue | service owners and incident management |

No single implementation team should silently own the policy, grant registry, enforcement code, and audit administration for consequential actions.

### 35. Measure effectiveness without optimizing clicks

Track populations and outcomes, not vanity totals:

| Metric | Question |
| --- | --- |
| decision latency by risk | Are gates proportional and adequately staffed? |
| denial reason distribution | Which policies, evidence, or requests are failing? |
| stale/revoked/replay prevention | Are exact-binding controls catching real drift? |
| emergency use and retrospective closure | Is break-glass rare, bounded, and reviewed? |
| approval-related incidents | Did an authorized action still create harm? |
| false-positive burden | Are people repeatedly asked to decide low-risk work? |
| authority hygiene | Are expired, broad, or unused grants removed? |

Faster approval is not automatically better. A healthy model reduces unnecessary gates while improving the quality and reconstructability of consequential decisions.

---

## Part XII — Productionization

### What the teaching system proves

For synthetic subjects, it proves exact-subject binding, direct and delegated scope checks, requester/author separation, dual control, current-parent validation, expiry, revocation, replay prevention, one-winner concurrent consumption, incident-scoped emergency containment, and audit-chain tamper detection.

### What it does not prove

- The synthetic session map is enterprise authentication.
- SQLite is the required production database.
- A hash chain alone provides immutable audit storage.
- A human understood the evidence or made a wise decision.
- A local commit is atomic with an external deployment API.
- The example policy satisfies every legal or regulatory obligation.
- `ELIGIBLE_FOR_ACCOUNTABLE_REVIEW` authorizes deployment or release.

### Production upgrades

Add workforce identity and strong authentication, authoritative group and resource ownership, durable and highly available policy and grant stores, signed policy bundles, denial-safe outages, database isolation appropriate to the workload, idempotent external operations, outbox/reconciliation, monitored revocation propagation, append-protected audit, secrets management, disaster recovery, approval-service SLOs, privileged-administration separation, and periodic access review.

Use an existing platform gate when it expresses the required semantics. GitHub environments, for example, support required reviewers and an option to prevent self-review, but the documented model allows one listed required reviewer to approve. A consequential dual-role enterprise decision may therefore need a custom protection service rather than assuming a platform click implements the whole policy.

### When not to use the full pattern

Do not build a bespoke approval control plane for every change. Low-risk, reversible work may use automated controls; a bounded repository workflow may be sufficient for a single review role; and safety-critical actions may be unsuitable for automated execution at all. Choose the smallest mechanism that faithfully enforces the decision semantics.

---

## Knowledge checkpoint

1. Why is `approved: true` insufficient?

   **Answer:** It does not bind authenticated authority to an exact subject, policy, time window, usage, or lifecycle.

2. A receipt approves artifact A and the branch now produces artifact B. Can it execute?

   **Answer:** No. The subject digest changed and approval must be re-established.

3. May a delegate receive a higher risk ceiling than the parent grant?

   **Answer:** No. Delegation must attenuate, never expand, parent authority.

4. Why recheck grants at execution?

   **Answer:** Authority or its parent may have been revoked or expired after receipt issuance.

5. What does the two-worker experiment prove?

   **Answer:** The modeled transaction permits exactly one receipt consumption and one registered operation under concurrent attempts.

6. Is emergency mode a general administrator bypass?

   **Answer:** No. It is incident-bound, time-bound, resource-scoped authorization for pre-defined containment actions.

7. What is the limitation of a local transaction around a remote deployment?

   **Answer:** It cannot atomically commit the remote effect; use idempotency, durable workflow state, and reconciliation.

## Staff-level architecture exercise

A SEV1 incident affects the underwriting assistant. A release-manager receipt approves model artifact A. An agent proposes artifact B with a faster rollback. The governance approver is unavailable. An on-call security lead has emergency authority to restore manual review, and an engineer proposes temporarily delegating production release authority to that lead.

Design the response. Identify:

1. which existing receipts are invalid for artifact B;
2. why the emergency role may contain harm but not inherit release authority;
3. whether the proposed delegation is an attenuation or expansion;
4. the exact containment subject and expiry;
5. the executor transaction and remote idempotency strategy;
6. audit and retrospective evidence; and
7. the separately authorized recovery path.

## Completion criteria

A completed submission includes a protected-decision model, risk matrix, versioned policy, trusted identity and authority inputs, exact-subject receipt, separation rules, attenuated delegation, single-use lifecycle, emergency containment design, reconstructable audit graph, 12 golden scenarios, concurrency proof, limitations, and a productionization plan.

## References

- [NIST SP 800-53 Rev. 5, AC-5 separation of duties and AC-6 least privilege](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)
- [NIST separation of duty glossary](https://csrc.nist.gov/glossary/term/separation_of_duty)
- [Open Policy Agent policy language](https://www.openpolicyagent.org/docs/policy-language)
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite write-ahead logging](https://www.sqlite.org/wal.html)
- [GitHub deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [GitHub reviewing deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
- [OpenSpec documentation](https://github.com/Fission-AI/OpenSpec/blob/main/docs/README.md)

## Next course

Course 24 turns security, quality, architecture, compliance, evidence, and approval obligations into CI/CD gates that fail safely and remain usable at enterprise scale.
