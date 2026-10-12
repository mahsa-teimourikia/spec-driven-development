# Course 14 — OpenSpec for Enterprise Change-Driven Spec-Driven Development

> Manage brownfield software as approved current truth plus explicit, reviewable change deltas—without allowing a framework or coding agent to approve policy, architecture, evidence, or release.

Course 13 placed an enterprise control layer around GitHub Spec Kit. Course 14 studies a different emphasis: OpenSpec treats the **change** as a first-class package and keeps current specifications separate from proposed deltas.

The working model is:

```text
approved baseline B + authorized semantic delta Δ → candidate target T
```

The equation is intentionally conditional. A syntactically valid delta does not become approved truth until the organization’s review, evidence, integration, and release controls say it may.

## Learning objectives

By the end of the course, you can:

1. explain OpenSpec’s current-specification, change-artifact, delta, sync, and archive model;
2. distinguish approved current truth, observed repository reality, proposed truth, and validated target truth;
3. author `ADDED`, `MODIFIED`, `REMOVED`, and `RENAMED` deltas with baseline-relative semantics;
4. validate requirement identity, revision, complete `FROM` state, authority, and affected invariants;
5. find semantic conflicts between concurrent changes even when Git reports no text conflict;
6. preserve company policy by reference and applicability instead of copying it into every change;
7. keep architecture proposals, ADR decisions, implementation tasks, and agent work units distinct;
8. scope evidence to changed claims plus the affected regression surface;
9. prevent agents from self-approving consequential lifecycle transitions;
10. integrate a validated delta into a new baseline while preserving historical provenance; and
11. choose OpenSpec, Spec Kit, a repository-native workflow, or a composition based on the problem rather than command names.

## Prerequisites

- [Course 03 — The specification hierarchy](../../beginner/03-the-specification-hierarchy/README.md)
- [Course 04 — Company vs project vs feature requirements](../../beginner/04-company-project-feature-requirements/README.md)
- [Course 07 — Acceptance criteria, invariants, and evidence](../../beginner/07-acceptance-criteria-invariants-evidence/README.md)
- [Course 10 — Implementation plans and agent work units](../../beginner/10-specification-to-implementation-plan/README.md)
- [Course 12 — SDD framework landscape](../02-sdd-framework-landscape-enterprise-operating-model/README.md)
- [Course 13 — GitHub Spec Kit for enterprise SDD](../03-github-spec-kit-enterprise-sdd/README.md)

You need Python 3.11 or later for the credential-free lab. OpenSpec itself is not required to execute the training fixture.

## Scenario, success criteria, and non-goals

Northstar Mutual already runs a document-processing platform:

```text
upload → approved extraction service → manual classification → underwriter review
```

Two teams independently propose changes against `REQ-DOC-014@3`:

- `AI-2310`: add AI-generated classification proposals while retaining human authority;
- `AI-2331`: add automated triage that assumes a different classification path.

The course succeeds when you can detect that both changes are individually baseline-valid but jointly unsafe without ordering or redesign. You will produce a bounded implementation package for `AI-2310`, hold `AI-2331` for rebase, and keep baseline integration outside agent authority.

This course does **not**:

- certify OpenSpec or claim the training adapter is production-ready;
- make Markdown an authorization system;
- treat a checked task list as independent evidence;
- teach every OpenSpec command or customization surface;
- grant the CLI, an AI assistant, or this lab release credentials; or
- claim that repository code alone is approved intent.

## 1. Why brownfield SDD needs a change model

In a greenfield exercise, a feature-oriented sequence can be enough:

```text
intent → specification → plan → tasks → implementation
```

In a long-lived system, several teams are changing a shared truth at once:

```text
approved behavior v4
       ├── change A
       ├── change B
       └── change C
```

Tickets and branches preserve delivery activity, but they do not necessarily say which approved behaviors are added, modified, removed, or renamed. OpenSpec’s core value is making that semantic delta explicit.

## 2. Four kinds of truth

Do not compress these into one artifact:

| Kind | Question | Typical evidence |
| --- | --- | --- |
| Approved baseline | What has an accountable owner accepted as current behavior? | versioned specs, ADR references, contracts |
| Repository reality | What does the selected code revision currently do? | discovery, tests, runtime observations |
| Proposed target | What would this change alter? | proposal, delta specs, design |
| Verified target | What exact implementation has supporting evidence? | revision-bound tests, evaluations, reviews |

Existing code is useful discovery evidence, but it can contain bugs, workarounds, deprecated behavior, and unauthorized decisions. It does not silently replace the approved baseline.

## 3. OpenSpec’s artifact model

The official OpenSpec v1.14.1 `spec-driven` schema defines four planning artifacts:

```text
proposal ──┬──> specs ──┐
           └──> design ─┼──> tasks ──> apply
                        ┘
```

- `proposal.md` explains why the change is needed, what changes, its capabilities, and impact.
- `specs/<capability>/spec.md` contains behavioral deltas.
- `design.md` explains consequential technical choices and may be omitted for a simple change.
- `tasks.md` is the tracked implementation checklist.

The workflow is action-oriented rather than a rigid one-way phase gate: a team can explore, propose, update artifacts, apply tasks, verify, sync, and archive as appropriate. Enterprise controls can add gates without pretending the framework itself owns organizational approval.

## 4. Baseline plus delta

Let:

```text
B = approved baseline specification
Δ = proposed semantic change
T = candidate target specification
```

Then:

```text
T = apply(B, Δ)
```

`apply` is valid only when:

1. the referenced baseline exists;
2. the baseline revision matches;
3. every `MODIFIED` requirement contains the complete prior requirement block;
4. the change owns or may propose changes to the target authority domain;
5. concurrent changes have been analyzed; and
6. removal and rename semantics are unambiguous.

This is optimistic concurrency control for specifications.

## 5. Delta operations

OpenSpec’s default delta vocabulary is intentionally small.

### ADDED

Use `ADDED` when the target behavior does not exist in the baseline:

```markdown
## ADDED Requirements

### Requirement: Classification proposal provenance
The system SHALL retain source, evidence, model, and governing-context provenance.

#### Scenario: Stored proposal
- **WHEN** a classification proposal is stored
- **THEN** its provenance references resolve to the exact inputs and versions
```

### MODIFIED

Use `MODIFIED` when existing behavior changes. Copy the entire existing requirement and all scenarios before editing it. Partial blocks can erase semantics at archive time.

```text
REQ-DOC-014@3
manual classification
       ↓ MODIFIED by AI-2310
REQ-DOC-014@4 candidate
AI proposal + governed human review
```

### REMOVED

Removal needs a reason and migration. It also needs impact analysis over contracts, data, tests, reporting, audit, and downstream readers.

```text
remove requirement
   → identify dependants
   → migrate
   → prove zero unsupported readers
   → retire
```

### RENAMED

Use `RENAMED` only when the name changes without changing semantics. If behavior changes too, use the relevant behavioral operation rather than hiding it inside a rename.

## 6. Current truth is organized by capability

OpenSpec stores current specifications under `openspec/specs/` and active changes under `openspec/changes/<change>/`. Each modified capability receives its own delta file at the matching capability path.

That path is semantic identity, not mere folder organization. Before creating a new capability, inspect current specs and reuse the exact path when the behavior already has an owner. Near-duplicate capabilities create competing truth.

## 7. Enterprise policy remains external authority

Northstar’s hierarchy is:

```text
enterprise policy and standards
          ↓ applicability
domain rules and contracts
          ↓
approved project baseline
          ↓
OpenSpec change delta
```

The change references `AI-030@7`; it does not copy the policy and relabel it as project-owned.

```text
canonical policy → effective context → change applicability
```

This keeps policy updates discoverable and prevents stale copies in project specs, change files, and agent instructions.

## 8. Protected authority

If a project change attempts to modify `AI-030`, the deterministic rule is:

```text
if target.authority > change.authority:
    BLOCK(PROTECTED_AUTHORITY_MUTATION)
```

The project may raise a policy-change or exception request. It cannot approve one. Accuracy results do not transfer decision rights.

## 9. Effective context

Before drafting `AI-2310`, resolve and pin:

- applicable enterprise policy and security standards;
- domain rules and contracts;
- project baseline and requirement revisions;
- architecture decisions;
- repository revision and discovery scope; and
- known concurrent changes.

The result is `CTX-AI-2310@4-training`. Every derived artifact retains that context identity and digest.

## 10. Concurrent changes

Two changes can both be valid relative to the same baseline:

```text
                 REQ-DOC-014@3
                    /      \
                   /        \
              AI-2310      AI-2331
                   \        /
                    conflict?
```

The validator must ask more than “did Git merge?”

### Text conflict versus semantic conflict

Git detects overlapping text edits. A change control plane must also detect incompatible behavior across different files and requirement IDs.

```text
AI-2310: ambiguous proposals require human review
AI-2331: high-confidence triage may bypass manual review
```

There may be no overlapping lines. The authority and outcome conflict remains real.

## 11. Conflict classes

The lab recognizes:

- `SHARED_REQUIREMENT_MODIFICATION`;
- `DIRECT_CONTRADICTION`;
- `INCOMPATIBLE_ARCHITECTURE`;
- `INCOMPATIBLE_CONTRACT`;
- `NFR_INTERACTION`;
- `AUTHORITY_CONFLICT`; and
- `MIGRATION_ORDER_CONFLICT`.

Classification is the start of review, not automatic resolution. A recorded conflict needs an accountable disposition: order, rebase, merge, split, redesign, or reject.

## 12. Change graph versus task graph

Do not collapse portfolio dependencies into implementation dependencies:

```text
portfolio → changes → requirements → designs → AWUs → tasks → evidence
```

A change dependency says one semantic target depends on another. A task dependency says one implementation step cannot safely start yet. They serve different decisions.

## 13. Brownfield design

Design starts from current architecture plus the delta:

```text
approved extraction service
          ↓
classification adapter
          ↓
deterministic validation
          ↓
classification proposal
          ↓
existing review workflow
```

Prefer `reuse → extend → adapt` before `replace → rebuild → introduce`, unless evidence supports the larger change.

If the design proposes Kafka, a new database, or a changed authorization boundary, record an architecture proposal. A reasonable idea is not an approved ADR.

## 14. Open questions and partial readiness

The pinned default OpenSpec schema does not define `questions.yaml`; the file in this workshop is an explicit enterprise adapter artifact. It preserves owner, status, and capability impact without pretending to be a built-in OpenSpec command or authority source.

An open question is typed and owner-routed:

```yaml
id: Q-AI2310-004
question: May high-confidence classifications bypass review?
owners: [AI Governance, Underwriting Risk]
status: OPEN
blocks: [automatic_classification_persistence]
```

Unaffected capability slices can proceed:

```text
proposal generation         READY
provenance                  READY
ambiguity handling          READY
automatic persistence       BLOCKED
```

If the blocked slice has independent value and authority, split it into another change. Do not silently convert the open question into an implementation assumption.

## 15. Task is not an agent work unit

OpenSpec tasks are useful tracked implementation steps. Before autonomous dispatch, enrich them with execution controls:

```yaml
id: AWU-AI2310-CLASSIFIER
change: AI-2310@2
requirements: [REQ-DOC-014@3, REQ-DOC-021@1]
writable_paths:
  - src/documents/classification/**
  - tests/documents/classification/**
protected_paths:
  - src/auth/**
  - src/underwriting/submission.py
stop_conditions:
  - contract_change_required
  - architecture_change_required
  - authority_conflict
required_evidence:
  - classification_evaluation
  - provenance_test
```

The AWU preserves change ancestry and narrows authority. The implementation agent may produce code and candidate tests; it may not issue its own independent conformance receipt.

AWUs, authority maps, evidence manifests, and integration receipts are enterprise composition artifacts in this course. They complement OpenSpec; they are not represented as native default-schema capabilities.

## 16. Evidence is delta-relative

Evidence scope is:

```text
changed claims + affected invariants + regression surface
```

For `AI-2310`, this includes classification evaluation, ambiguity routing, injection resistance, provenance, the review contract, and regression coverage for manual processing.

Two questions remain separate:

1. Did the new behavior work?
2. Did unchanged affected obligations remain true?

Passing only the first is not change conformance.

## 17. Evidence independence and subject binding

Every evidence record identifies:

- the specific claim or invariant;
- producer and independence class;
- implementation and specification revisions;
- execution time and result; and
- limitations.

A coding agent’s “all tasks complete” message is useful completion provenance, not independent evidence or release authority.

## 18. Sync, archive, and enterprise integration

In OpenSpec, sync merges delta specs into current specs without closing the change. Archive can validate, apply deltas, and move the completed change to dated history.

The framework operation is not the whole enterprise decision:

```text
code merged
  → independent evidence complete
  → architecture and policy decisions resolved
  → integration owner authorizes exact revisions
  → delta applied atomically
  → new baseline validated
  → change archived
  → release remains separately governed
```

OpenSpec v1.14.1’s CLI archive path validates by default and uses recovery behavior around spec mutation and final movement. An enterprise wrapper should still verify organization-specific evidence, authority, concurrency, and release state before invoking it.

## 19. Archive is not deletion

Archive preserves the proposal, design, tasks, and delta as history while the live specs describe current truth:

```text
REQ-DOC-014@3 + approved AI-2310 delta
                 ↓
REQ-DOC-014@4 + archived AI-2310 provenance
```

This compacts active truth without erasing why it changed. Do not archive merely because a pull request merged.

## 20. Change revision and discovery feedback

Implementation may reveal a real constraint. Route it by meaning:

```text
discovery
   ├── design-only consequence → revise design/tasks with traceability
   └── requirement consequence → accountable owner decision → new change revision
```

Never rewrite history to make the original proposal appear correct. Preserve `AI-2310@1`, the decision record, and `AI-2310@2`.

## 21. Lifecycle states

A useful enterprise lifecycle is:

```text
DRAFT → CLARIFYING → READY_FOR_REVIEW → APPROVED
      → IMPLEMENTING → VERIFYING → READY_FOR_INTEGRATION → ARCHIVED
```

Exceptional states include `BLOCKED`, `REJECTED`, `SUPERSEDED`, and `WITHDRAWN`.

States are application-owned contracts. Coding agents can report task completion; they cannot self-transition a consequential change to approved, released, or archived.

## 22. Multiple decision owners

One generic “owner” is not enough:

| Decision | Accountable authority |
| --- | --- |
| Business scope | Underwriting Operations |
| Architecture | Architecture Council |
| Injection controls | Product Security |
| Authoritative AI mutation | AI Governance and Underwriting Risk |
| Release | Delivery control plane and release owner |

Precise ownership produces precise escalation.

## 23. Change sizing

A change should be semantically coherent, reviewable, independently verifiable, and reasonably bounded.

“Modernize document processing with AI” is too broad. “Add field,” “add enum,” and “add test” are implementation tasks, not meaningful behavior changes. The right unit changes an understandable system promise.

## 24. Multi-repository changes

For a parent change spanning repositories:

- keep canonical requirement identity and target semantics in the parent;
- let child packages specialize local implementation and evidence;
- prohibit children from weakening the parent;
- pin contract versions and integration order; and
- require system-level evidence before parent integration.

Local success does not prove cross-repository conformance.

## 25. Threat model

Treat proposal text, repository content, tool output, generated deltas, and agent messages as untrusted inputs. The trusted application validates:

- identity and authority from authenticated state;
- context and baseline digests;
- delta operations and complete prior content;
- capability paths and requirement IDs;
- protected targets;
- open questions and conflict dispositions;
- evidence subjects and producer independence; and
- state-transition and integration receipts.

Prompt instructions alone cannot enforce these boundaries.

## 26. Technology landscape

| Approach | Strength | Limitation | Best fit |
| --- | --- | --- | --- |
| OpenSpec | First-class change packages and delta-to-baseline evolution | Does not become enterprise authority merely by being adopted | Brownfield systems and concurrent change |
| GitHub Spec Kit | Rich feature workflow and extensible process harness | Feature artifacts need explicit baseline/change semantics for some portfolios | Feature-oriented delivery |
| Repository-native ADR/spec process | Maximum fit and control | Organization owns all tooling, consistency, and upgrades | Mature internal platforms |
| Ticket + PR only | Low ceremony | Weak semantic change history and impact reasoning | Low-risk, local, reversible work |

Framework selection is contextual. A company may use OpenSpec-style portfolio change governance and Spec Kit-style feature implementation, provided artifact ownership and duplication are explicit.

## 27. When not to use the full process

Use a lighter path for a typo, safe documentation correction, mechanical formatting, or another low-consequence reversible change with no behavioral contract impact.

Escalate process depth for shared contracts, protected authority, concurrent semantic edits, migrations, regulated data, irreversible effects, or costly rollback. Process depth follows consequence and uncertainty—not file count.

## 28. State of practice

Established practice includes versioned current specs, small reviewable changes, requirement scenarios, CI validation, ADRs, and independent tests. OpenSpec packages these around a change-oriented repository model.

Emerging enterprise practice adds external effective-context resolution, authority maps, evidence manifests, policy gates, multi-repository parent/child changes, and semantic conflict graphs.

The research frontier includes reliable semantic-diff detection, conflict prediction across heterogeneous artifacts, proof-preserving spec compression, and calibrated agent assistance for impact analysis. These remain open problems; the deterministic lab supports only its labelled fixture.

## 29. Worked Northstar result

The reference package concludes:

```text
AI-2310
  baseline-valid
  protected policy preserved
  bounded implementation package ready for owner review

AI-2331
  individually baseline-valid
  conflicts with AI-2310 on REQ-DOC-014@3
  blocked pending ordering and rebase

baseline
  unchanged

archive/release
  not authorized
```

This is partial readiness, not process failure.

## 30. Guided lab

Open the [Northstar OpenSpec enterprise-change workshop](northstar-openspec-change/README.md), then run:

```bash
python3 curriculum/intermediate/04-openspec-enterprise-change-driven-sdd/northstar-openspec-change/lab.py
```

The lab reports:

- baseline and context integrity;
- delta application and affected invariants;
- concurrent semantic conflicts;
- task-to-AWU ancestry and boundaries;
- evidence coverage and independence;
- integration and archive eligibility;
- 10 golden scenarios; and
- 40 labelled control mutations.

Use the [guided notebook](northstar-openspec-change/openspec_enterprise_change.ipynb) for the complete experiment sequence.

## 31. Experiments

### Experiment A — stale baseline

Change `REQ-DOC-014@3` to `@2` in a delta. Observe that the correct result is `REBASE_REQUIRED`, not best-effort application.

### Experiment B — hidden semantic conflict

Remove the conflict register while keeping both changes. Git still has separate directories; the enterprise validator blocks the portfolio.

### Experiment C — delta-only evidence

Keep classification evaluation but remove manual-workflow regression evidence. The new behavior may pass while an unchanged obligation fails.

### Experiment D — premature archive

Request archive before owner review and exact-revision evidence. The validator keeps the baseline unchanged.

## 32. Evaluation interpretation

The conformance and mutation scores answer narrow questions:

```text
golden scenario match = correct labelled outcome / 10 fixture scenarios
mutation detection = expected control code observed / 40 injected mutations
```

They do not measure general OpenSpec correctness, model quality, production safety, or vendor certification.

## 33. Failure modes

| Failure | Why it is unsafe | Control |
| --- | --- | --- |
| Copy policy into every change | authority and revision drift | source-backed effective context |
| Partial `MODIFIED` block | lost scenarios on integration | full baseline-block match |
| Change targets stale revision | overwrites newer truth | optimistic concurrency check |
| Git-only conflict detection | misses semantic collisions | requirement and dependency graph |
| Design introduces infrastructure | launders architecture approval | proposal + ADR routing |
| Task dispatched directly | no bounded authority or evidence | AWU enrichment |
| Agent self-attests | producer evaluates itself | independent evidence |
| PR merge triggers archive | code state confused with approved truth | integration gate |
| Open question becomes assumption | missing decision hidden | typed question and capability block |
| Child repo weakens parent | cross-repository meaning drifts | canonical parent IDs and validation |

## 34. Production upgrade path

| Training fixture | Production upgrade |
| --- | --- |
| JSON authority map | authenticated policy/ownership service |
| local digests | signed provenance and immutable artifact storage |
| synthetic evidence records | CI, evaluation, security, and runtime attestations |
| deterministic conflict rules | graph index plus owner-reviewed semantic analysis |
| training state machine | transactional workflow service with optimistic locking |
| archive eligibility report | single-use integration authorization bound to exact revisions |
| one repository | parent/child change graph and contract registry |
| local logs | privacy-safe audit telemetry and retention controls |

## 35. Exercises

1. Add a `REMOVED` delta for a legacy category field. Model migration evidence and zero-reader proof.
2. Introduce a third change that alters an NFR rather than `REQ-DOC-014`. Explain whether it conflicts semantically.
3. Split automatic persistence into `AI-2310B` while allowing proposal generation to proceed.
4. Add an architecture proposal for a new event stream and prove the coding agent cannot approve it.
5. Design an integration receipt bound to baseline digest, change revision, implementation digest, policy revision, approver identity, expiry, and single-use state.
6. Compare a single-agent and multi-agent implementation topology without changing governance depth.
7. Decide whether a documentation-only OpenSpec change should set `skip_specs: true`; justify the decision from observable behavior.
8. Model a bulk-archive collision and explain why chronological order alone is not a semantic resolution policy.

## 36. Review questions

1. Why does valid syntax not make a delta authorized?
2. What must match before a `MODIFIED` requirement can be applied?
3. How can changes to different requirement IDs still conflict?
4. Why are delta evidence and regression evidence both necessary?
5. What does sync do that archive does not?
6. Why should a change package preserve company policy by reference?
7. Which lifecycle transitions may an implementation agent report, and which require external authority?
8. When is OpenSpec a stronger fit than a feature-oriented workflow?

## 37. Key takeaways

1. Brownfield SDD manages change relative to approved current truth.
2. `baseline + delta` yields only a candidate target until authority and evidence gates pass.
3. Company requirements remain canonical and are inherited through applicability.
4. Concurrent changes can conflict semantically without a Git conflict.
5. OpenSpec tasks still need bounded AWUs for autonomous execution.
6. Evidence covers changed claims and affected unchanged invariants.
7. Code merge, spec sync, archive, and production release are distinct events.
8. Coding agents propose and implement; trusted systems validate, authorize, integrate, and release.

## References

- [OpenSpec repository](https://github.com/Fission-AI/OpenSpec)
- [OpenSpec concepts](https://github.com/Fission-AI/OpenSpec/blob/v1.14.1/docs/concepts.md)
- [OpenSpec workflows](https://github.com/Fission-AI/OpenSpec/blob/v1.14.1/docs/workflows.md)
- [OpenSpec commands](https://github.com/Fission-AI/OpenSpec/blob/v1.14.1/docs/commands.md)
- [OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/v1.14.1/docs/cli.md)
- [OpenSpec `spec-driven` schema](https://github.com/Fission-AI/OpenSpec/blob/v1.14.1/schemas/spec-driven/schema.yaml)
- [GitHub Spec Kit](https://github.github.com/spec-kit/)
- [Architecture Decision Records](https://adr.github.io/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

The framework details in this course are pinned to OpenSpec v1.14.1 and the resolved release commit recorded in the workshop snapshot. Revalidate the snapshot before adopting a newer release.
