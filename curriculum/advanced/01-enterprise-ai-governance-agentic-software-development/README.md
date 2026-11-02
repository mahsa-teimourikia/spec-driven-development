# Course 25 — Enterprise AI Governance for Agentic Software Development

> Enterprise Spec-Driven Development · Part V: Enterprise Controls · Course 25 of 38

**Level:** Advanced / Staff AI Scientist, AI Technical Lead, and Governance Engineer

**Estimated time:** 8–12 hours

**Prerequisites:** Courses 15–17 and 23–24

**Case study:** Northstar Mutual — governance of the AI Underwriting Assistant

**Practical stack:** Python, JSON policy records, Rego concepts, SQLite, signed teaching evidence, and lifecycle evaluation

## Why this course matters

Course 24 proved that an exact reviewed artifact and AI configuration reached production through trusted release controls. That still does not answer whether the AI use case should exist, which model and data uses are permitted, how much autonomy is acceptable, who owns the residual risk, or when an approved system must be reassessed.

A technically correct system can remain outside its approved purpose. Northstar's Broker Document Review may pass its software tests while using a revoked model, processing data in an unresolved location, bypassing human oversight, or gaining an authoritative mutation tool that was never approved.

The central principle is:

> Agents may propose governance artifacts and remediation. Trusted organizational records, accountable decision-makers, independent evidence, and protected enforcement determine whether an exact bounded use is allowed.

This course turns governance principles into versioned specifications, relational registries, risk-triggered controls, authenticated evidence, exact-subject approvals, runtime restrictions, and change-impact rules.

## Learning objectives

By the end, you should be able to:

1. Design an enterprise AI-governance operating model across the system lifecycle.
2. Distinguish model, application, agent, and organizational governance.
3. Create authoritative use-case, model, agent, tool, evidence, and decision records.
4. Classify systems by context, impact, autonomy, data, exposure, uncertainty, and reversibility.
5. Combine scored assessment with mandatory policy floors so critical risk cannot be averaged away.
6. Translate principles into executable requirements, controls, and evidence contracts.
7. Bind human oversight and delegated authority to exact protected actions.
8. Select evaluation and monitoring obligations from approved risk policy.
9. Trigger targeted reassessment after model, prompt, retrieval, tool, policy, or purpose changes.
10. Integrate AI governance with specifications, pull requests, CI/CD, and runtime enforcement.

## Run the course

From the repository root:

```bash
python3 curriculum/advanced/01-enterprise-ai-governance-agentic-software-development/northstar-ai-governance/lab.py
python3 -m unittest tests.test_course_25 -v
```

Then open the guided [AI-governance notebook](northstar-ai-governance/ai_governance.ipynb) from the `northstar-ai-governance` directory. The [lab guide](northstar-ai-governance/README.md) explains the artifact package and workshop.

---

# Part I — Governance as an engineering discipline

## 1. Principles are necessary but not executable

“Meaningful human oversight” is a governance objective. Engineering needs a protected decision boundary:

```yaml
requirement:
  id: GOV-HUMAN-001
  owner: Underwriting Governance
  statement: >
    Ambiguous underwriting document classifications SHALL require an
    authenticated, authorized human decision before satisfying an
    underwriting requirement.
  enforcement:
    - review-service authorization
    - underwriting transition guard
  verification:
    - ambiguity population evaluation
    - unauthorized mutation negative test
    - review-bypass runtime monitor
```

A prompt saying “never bypass review” can guide behavior. It cannot authorize or protect the underwriting state transition.

## 2. The governance-to-enforcement chain

```text
governance objectives and risk appetite
                  ↓
authoritative policies and accountable ownership
                  ↓
system context and impact assessment
                  ↓
executable obligations and applicability
                  ↓
engineering and runtime enforcement
                  ↓
independent, revision-bound evidence
                  ↓
accountable authorization and reassessment
```

Each link answers a different question. A control can be correctly implemented yet inapplicable; applicable yet unsupported by current evidence; evidenced yet not authorized; authorized yet no longer current after a component change.

## 3. Decision rights

| Decision | Accountable authority | Agent role |
|---|---|---|
| Organizational AI risk methodology | Enterprise governance | Identify gaps; propose analysis |
| Business purpose and owner | Business authority | Draft registration |
| Model permitted use | Model governance | Resolve the approved record |
| Agent tools and autonomy | Product, security, and governance owners | Propose least-privilege capability |
| Evidence result | Independent evaluator | Execute only when delegated; never self-attest |
| Residual-risk acceptance | Named risk owner | Present evidence and alternatives |
| Protected execution | Trusted application boundary | Request the exact authorized action |

Role labels in a prompt do not confer these rights. Identity and authority come from authenticated application state.

---

# Part II — Frameworks without compliance theater

## 4. Complementary sources

| Source | Primary role | Engineering use | Boundary |
|---|---|---|---|
| NIST AI RMF | Voluntary AI risk management | Organize Govern, Map, Measure, Manage outcomes | Not a certification or ordered checklist |
| ISO/IEC 42001:2023 | AI management-system requirements | Organizational roles, lifecycle processes, continual improvement | Does not prove a particular model is accurate |
| ISO/IEC 23894 | AI risk-management guidance | Risk identification, analysis, treatment, monitoring | Must be adapted to organizational context |
| ISO/IEC 27001 | Information-security management | Integrate AI controls with the ISMS | Does not replace AI-specific evaluation |
| EU AI Act | Legal obligations within scope | Applicability and role analysis with qualified counsel | Classification depends on facts, role, purpose, and current law |
| OWASP LLM and Agentic guidance | Application and agent security risks | Threat modelling, tests, and runtime controls | Security guidance is not full governance |

This course maps these sources to an engineering operating model. It does **not** claim certification, legal compliance, or universal applicability. As of November 2026, NIST states that AI RMF 1.0 is being revised; pin the source and date used in each organizational mapping.

## 5. Adapt the NIST functions to durable artifacts

| Function | Durable artifacts |
|---|---|
| GOVERN | Policy registry, authority matrix, decision and exception records |
| MAP | Use-case registry, stakeholder/context record, data flow, impact assessment |
| MEASURE | Evaluation contract, labelled populations, security tests, uncertainty evidence |
| MANAGE | Risk treatment, restrictions, release gates, monitoring, incident response, retirement |

Govern is cross-cutting. The functions inform one another throughout the lifecycle; they are not a one-time waterfall.

---

# Part III — Govern the system, not only the model

## 6. Four related layers

### Organizational governance

Defines policy, risk appetite, decision rights, assurance, exceptions, incidents, and continual improvement.

### Model governance

Tracks provider, model identity and revision, provenance, permitted uses, limitations, evaluations, dependencies, and vendor changes.

### Application governance

Governs data access, retrieval, prompts, output validation, user experience, business workflow, and consequential impact.

### Agent governance

Governs workload identity, tools, delegated scope, autonomy, side effects, budgets, retries, memory, handoffs, and termination.

An approved model is not automatically approved for every application. An approved application is not automatically approved to gain an authoritative tool.

## 7. Authority expansion is a system change

Changing a classifier from proposal-only to “update requirement status above 98% confidence” may be a tiny diff. It changes the system's authority, hazards, human-oversight design, evaluation obligations, and residual risk. Confidence is not authorization, and calibration on one population does not grant mutation rights.

---

# Part IV — Relational governance registries

## 8. Inventory is the foundation

Northstar must be able to answer:

- Which use cases depend on model revision 12?
- Which agents have authoritative tools?
- Which systems process personal information?
- Which approvals depend on policy revision 4?
- Which evaluation expires next week?
- Which production capability must be contained after a protected invariant fails?

A spreadsheet can begin discovery, but operational governance needs stable identities and relations:

```text
business use case
  ├─ application and business owner
  ├─ model revision and permitted task
  ├─ agent revision, tools, and autonomy
  ├─ data classification and residency
  ├─ impact assessment and treatment
  ├─ evaluation and oversight evidence
  ├─ approval and exception records
  └─ runtime signals and incidents
```

## 9. Registration is not approval

Use an explicit lifecycle:

```text
DISCOVERED → REGISTERED → RISK_ASSESSMENT_REQUIRED → UNDER_REVIEW
     → APPROVED_FOR_BOUNDED_USE → ACTIVE
     → REASSESSMENT_REQUIRED → SUSPENDED or RETIRED
```

The coding agent may submit a registration proposal. Only the protected governance workflow can transition the authoritative record.

## 10. Provenance for governance facts

Consequential records need stable ID, scope, source/version, owner, timestamps, lifecycle, and digest. A schema-valid registry record is still not necessarily authentic, current, or authorized. Resolve current records from trusted systems at the point of use.

---

# Part V — Contextual risk and policy floors

## 11. Risk is not a model property

The same foundation model can summarize internal documentation, propose underwriting risk factors, or autonomously modify a policy decision. The operating context changes the consequence even when model weights do not.

The lab evaluates six illustrative dimensions from 1–3:

- decision consequence;
- autonomy;
- data sensitivity;
- external exposure;
- model uncertainty; and
- reversibility.

This score teaches mechanics. It is not a validated regulatory method.

## 12. Prevent averaging away critical hazards

Northstar combines the scored tier with policy floors:

```text
effective risk tier = max(scored tier, mandatory policy floors)
```

An authoritative mutation tool or high-autonomy workflow forces the consequential path even if other dimensions score low. The agent cannot lower its own tier because the control plane independently resolves assessment and capability facts.

## 13. Risk selects obligations

| Control | Low | Moderate | Consequential |
|---|---|---|---|
| Registration | Required | Required | Required |
| Assessment | Basic | Structured | Comprehensive |
| Evaluation | Task-focused | Risk-based | Independent plus negative tests |
| Human oversight | As applicable | Triggered | Protected decision boundary |
| Security/privacy | Baseline | Enhanced | Specialized and independent |
| Authorization | Standard | Governed | Exact-subject accountable authority |
| Monitoring | Baseline | Enhanced | Protected invariants and containment |

Specific hazards or law can impose stronger requirements than the aggregate tier.

---

# Part VI — Executable governance controls

## 14. One policy becomes several controls

Policy: “AI-generated underwriting recommendations remain advisory until an authorized human approves the consequential decision.”

Derived obligations:

1. AI output cannot directly mutate underwriting state.
2. The protected API derives identity and scope from authenticated state.
3. Human approval names the exact subject, action, policy, approver, and expiry.
4. A changed proposal invalidates approval.
5. The executor atomically consumes approval and records the operation.
6. Runtime monitoring detects review bypass in the applicable population.

No single prompt, test, or policy rule proves all six.

## 15. Match controls to mechanisms

| Obligation | Primary mechanism |
|---|---|
| Approved model and intended task | Model/use-case registry and gateway |
| Authorized data | Identity, data layer, purpose and residency controls |
| Human decision | Approval service and transition guard |
| Output shape | Schema plus semantic validation |
| Grounding | Evidence resolver and claim-support evaluation |
| Agent action | Narrow tool, policy, capability grant, executor |
| Evaluation threshold | Owner-approved contract and independent result |
| Exception | Scoped, expiring, independently approved exception record |
| Runtime conformance | Authenticated observations and incident response |

## 16. Policy-as-code needs trusted inputs

The included [Rego excerpt](northstar-ai-governance/policies/governance.rego) illustrates a declarative decision. The executable Python boundary additionally:

- resolves canonical registry relationships;
- derives the risk tier and mandatory floors;
- authenticates evidence producers;
- binds evidence to model, agent, policy, and full subject digest;
- distinguishes `BLOCKED` from `INSUFFICIENT_EVIDENCE`;
- authenticates human and executor principals;
- rechecks current state; and
- atomically consumes a single-use receipt.

A caller-supplied `model_approved: true` is not an authoritative input.

---

# Part VII — Evidence, oversight, and uncertainty

## 17. Four decision states

| State | Meaning | Protected action |
|---|---|---|
| `ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL` | Controls and current evidence pass | Still not authorized |
| `INSUFFICIENT_EVIDENCE` | A required fact is absent, stale, expired, or unresolved | Deny and obtain evidence |
| `BLOCKED` | A known prohibition or failed mandatory control applies | Deny and remediate or redesign |
| `ALLOWED` | Exact current subject has current evidence and consumed approval | Execute only the named bounded action |

These states avoid turning uncertainty into silent success or treating every unknown as a permanent prohibition.

## 18. Evaluation is an evidence contract

Record population, labels, provenance, metric numerator/denominator, slices, threshold owner, model/application dependencies, producer, issue/expiry, limitations, and exact subject. Separate:

- model/component quality;
- end-to-end workflow outcome;
- safety-policy violations;
- blocked attempts;
- actual forbidden outcomes; and
- valid work blocked.

The lab's labelled cases prove only its deterministic fixture. They are not a benchmark of real model quality.

## 19. Human oversight must be operational

“Human in the loop” is not satisfied by showing a confirmation dialog. Ask whether the reviewer has authenticated authority, enough information and time, independent evidence, a real ability to reject, and a protected boundary that prevents bypass.

---

# Part VIII — Lifecycle and reassessment

## 20. Approval is bounded, not permanent

Reassess when relevant facts change:

- model/provider/revision;
- prompt or system instructions;
- retrieval data or data authority;
- tools, permissions, identity, or autonomy;
- intended purpose, users, population, or geography;
- evaluation contract or policy;
- incident, drift, new hazard, or material performance change.

The change-impact map selects affected obligations rather than blindly reusing every green result or rerunning everything.

## 21. Runtime governance

Production controls should detect purpose or scope drift, unauthorized tool calls, human-review bypass, tenant isolation failure, evaluation drift, data-policy violations, incidents, and expired approvals. A protected invariant failure can require capability containment even when infrastructure is healthy.

Reassessment may continue, restrict, suspend, remediate, or retire the system. The coding agent can propose the response; accountable authority owns the decision.

---

# Part IX — Practical lab

## 22. Architecture

```text
agent proposal
      ↓
canonical use-case/model/agent/tool registry
      ↓
contextual risk + mandatory policy floors
      ↓
required-control and evidence selection
      ↓
authenticated revision-bound evidence
      ↓
accountable exact-subject approval
      ↓
protected point-of-use revalidation + atomic consumption
      ↓
bounded ALLOWED operation or typed denial
```

The standard-library lab executes 13 golden scenarios and 13 labelled adversarial decisions. It rejects self-downgraded risk, revoked models, unknown residency, missing oversight, unauthorized autonomy, forged/wrong-subject evidence, agent self-approval, stale approval, and replay; authenticated protected-invariant failure suspends the capability.

## 23. Failure-injection matrix

| Mutation | Expected behavior |
|---|---|
| Agent changes its risk tier | `RISK_TIER_MISMATCH` |
| Approved model becomes revoked | `MODEL_NOT_APPROVED` |
| Privacy evidence is absent | `INSUFFICIENT_EVIDENCE` |
| Evidence is forged | Reject before registration |
| Authoritative mutation tool is added | Consequential floor plus `UNAUTHORIZED_AUTONOMY` |
| Human oversight becomes unverified | `HUMAN_OVERSIGHT_UNVERIFIED` |
| Approval names a different digest | `APPROVAL_SUBJECT_MISMATCH` |
| Agent requests self-approval | `APPROVER_NOT_AUTHORIZED` |
| Policy changes before execution | Stale approval denial |
| Two executions race on one receipt | Exactly one `ALLOWED` |

## 24. Production upgrades

Replace teaching HMAC fixtures with approved workload identity, managed keys, rotation/revocation, durable registry services, database migrations and availability design, independent evaluators, policy-bundle signing, jurisdictional applicability, privacy impact assessment, real model gateway enforcement, runtime telemetry, incident integration, retention/deletion controls, and qualified legal/compliance review.

The local `ALLOWED` result authorizes no real production action.

---

# Part X — Staff-level design exercise

Northstar's advisory assistant is approved for human-reviewed classification proposals. The product team wants autonomous underwriting-status updates above 98% model confidence.

Produce a governance response that addresses:

1. why this is a system-authority change rather than only a model threshold change;
2. intended purpose, affected stakeholders, reversibility, and failure modes;
3. updated risk tier and mandatory policy floors;
4. new tool identity, authorization, idempotency, approval, and audit boundaries;
5. evaluation populations, calibration, negative tests, and human-oversight evidence;
6. change-impact and invalidated approvals;
7. accountable approvers and residual-risk owner;
8. staged activation, runtime invariants, containment, and retirement; and
9. the simpler proposal-only alternative.

Use the [starter governance design](northstar-ai-governance/workshop/starter/governance-design.json), then compare with the [reference design](northstar-ai-governance/reference/governance-design.json).

## Checkpoint

An agent's model is approved, its evaluation passes, and its proposed tool arguments are schema-valid. May it update underwriting state?

1. Yes; the three checks establish authority.
2. Only if current policy, authenticated identity, delegated scope, exact-subject approval, protected execution, and all other applicable controls independently allow that action.
3. Yes, when confidence exceeds 98%.

**Answer:** 2. Model approval, evaluation, and schema validity are necessary inputs in some designs; none grants business authority.

## Completion criteria

Produce a canonical use-case record, relational model/agent/tool registry, approved impact assessment, governance-to-control trace, independently verified evidence set, exact-subject decision, change-impact result, negative-test report, and explicit non-authorities.

**Key takeaway:** Enterprise AI governance becomes operational when purpose, risk, authority, controls, evidence, and lifecycle decisions are versioned and enforced at trusted boundaries—not when an agent or checklist declares the system responsible.

## Authoritative references

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST AI RMF Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)
- [European Commission — AI regulatory framework](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [Open Policy Agent policy language](https://www.openpolicyagent.org/docs/policy-language)

Framework and legal applicability should be rechecked against current authoritative sources and qualified organizational owners. The cited snapshot was reviewed on 2026-11-01.

Next: Course 26 — Architecture Governance for Agentic SDD.
