# Lab B fixture — Northstar Underwriter

This miniature repository turns Course 01's control-plane ideas into repository work. It is deliberately self-contained and credential-free. No code calls a model, cloud service, or external network.

The only initial request is [JIRA-4821](ticket/JIRA-4821.md). Before changing code, inspect the distributed sources of authority:

- `context/organization/` — enterprise privacy, delivery, and assurance policy;
- `context/platform/` — approved AI-platform controls;
- `context/domain/` — insurance-domain obligations;
- `context/project/` — Underwriter Assistant architecture;
- `context/feature/` — feature acceptance behavior;
- `docs/decisions/` — architecture decision history; and
- `AGENTS.md` — repository-local operating instructions, not an authorization mechanism.

Two candidate changes simulate coding-agent output:

- `changes/unsafe/` is coherent code produced from the ticket alone. It deliberately violates policy and architecture for educational detection.
- `changes/governed/` implements the same behavior within the resolved constraints.

From the parent course directory, run:

```bash
python3 repo_lab.py --candidate unsafe
python3 repo_lab.py --candidate governed
python3 repo_lab.py --candidate governed --approve
python3 repo_lab.py --candidate all
```

Evidence is written to `build/course01-evidence/`, which is ignored by Git. Inspect the generated requirement set, applicability decisions, test result, architecture and policy findings, traceability map, approvals, and release summary.

## Learner challenge

1. Read only the ticket and predict what a coding agent might reasonably choose.
2. Inventory the authoritative context before reading either candidate.
3. Explain why each requirement is applicable, not applicable, or uncertain.
4. Run the unsafe candidate and map every finding to the control that detected it.
5. Identify the risks the checks explicitly say they still cannot establish.
6. Run the governed candidate before and after approval.
7. Add an applicability rule, inject a conflict, or remove provenance and extend the tests.

The fixture never contains a usable credential. Credential-like text in the unsafe candidate is a clearly labeled inert sentinel used to test secret-detection logic.
