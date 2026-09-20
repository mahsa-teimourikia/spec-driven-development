# Lab B fixture — Northstar Underwriter

This miniature repository turns Course 01's control-plane ideas into repository work. It is deliberately self-contained and credential-free. No code calls a model, cloud service, or external network.

The only initial request is the deliberately inadequate [JIRA-4821](ticket/JIRA-4821.md). It includes a product comment proposing a direct public-model call; that comment conflicts with enterprise and platform controls and cannot authorize an exception. Before changing code, inspect the distributed sources of authority:

- `context/organization/` — enterprise privacy, delivery, and assurance policy;
- `context/platform/` — approved AI-platform controls;
- `context/domain/` — insurance-domain obligations;
- `context/project/` — Underwriter Assistant architecture;
- `context/feature/` — feature acceptance behavior;
- `docs/decisions/` — architecture decision history; and
- `AGENTS.md` — repository-local operating instructions, not an authorization mechanism.

Human-readable source artifacts are under `enterprise/` and `platform/`. The corresponding JSON in `context/` is the course's machine-readable control registry. The pair teaches a crucial production concern: extraction is a governed transformation, and a structured record is only useful when it retains immutable source provenance.

The learner starts in `workshop/starter/policy-document-qa/`, records unknowns and applicability decisions, and writes a change package. The completed reference package is in `changes/policy-document-qa/`; do not read it until you have made your own decisions.

Two candidate changes simulate coding-agent output:

- `changes/unsafe/` is coherent code produced from the ticket alone. It deliberately violates policy and architecture for educational detection.
- `changes/governed/` implements the same behavior within the resolved constraints.

From the parent course directory, run:

```bash
python3 repo_lab.py --candidate unsafe
python3 repo_lab.py --candidate governed
python3 repo_lab.py --candidate governed --approval-receipts northstar-underwriter/approvals/training-receipts.json
python3 repo_lab.py --candidate all
```

Evidence is written to `build/course01-evidence/`, which is ignored by Git. Inspect the generated requirement set, applicability decisions, candidate-owned and independent test results, evaluation metrics, architecture and policy findings, multi-stage traceability matrix, approval receipt verification, human-readable gate report, and release summary.

## Learner challenge

1. Read only the ticket and predict what a coding agent might reasonably choose.
2. Inventory the authoritative context before reading either candidate.
3. Explain why each requirement is applicable, not applicable, or uncertain.
4. Run the unsafe candidate and map every finding to the control that detected it.
5. Identify the risks the checks explicitly say they still cannot establish.
6. Run the governed candidate before and after approval.
7. Compare the candidate's own passing tests with the independent gates. Explain why self-authored tests are not an approval signal.
8. Add an applicability rule, inject a conflict, or remove provenance and extend the tests.

`PASS` means the classroom change is eligible for a controlled merge after verified training receipts. It never means production release. The generated report keeps production release blocked while runtime tenant-isolation, residency, and domain-quality evidence is pending.

The fixture never contains a usable credential. Credential-like text in the unsafe candidate is a clearly labeled inert sentinel used to test secret-detection logic.
