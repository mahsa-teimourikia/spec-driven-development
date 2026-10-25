# Northstar Mutual brownfield modernization lab

This workshop turns Course 18 into a runnable change package for `AI-2410`.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/08-brownfield-development-with-agentic-coding-agents/northstar-underwriter-modernization/lab.py
python3 -m unittest tests/test_course_18.py
```

The runner prints a JSON report and makes no network calls.

## Learning path

1. Read `specs/AI-2410/discovery.md` and inspect the revision-bound discovery manifest.
2. Compare characterization evidence with the behavior dispositions.
3. Verify that the semantic delta adds summary proposals without modifying deterministic risk classification.
4. Trace the consumer graph into the regression plan.
5. Run the lab and inspect the ten failure experiments.
6. Compare `candidate/direct-agent-replacement.json` with `reference/modernization-package.json`.
7. Complete the five decisions in `workshop/starter/modernization-package.json`.
8. Use the notebook to mutate staleness, compatibility, migration, and authority inputs.

## Package map

| Path | Purpose |
| --- | --- |
| `brownfield_app/contracts.py` | Typed subjects, proposals, findings, and behavior records |
| `brownfield_app/legacy.py` | Approved deterministic baseline and additive providers |
| `brownfield_app/discovery.py` | Discovery, disposition, and regression-selection checks |
| `brownfield_app/governance.py` | Trusted freshness, compatibility, authorization, and change-package checks |
| `brownfield_app/migration.py` | Transactional idempotency at the proposal state boundary |
| `fixtures/` | Repository/runtime teaching evidence and submissions |
| `specs/AI-2410/` | Discovery, baseline, delta, impact, regression, rollout, and traceability |
| `conformance-suite.json` | Twelve golden decisions |
| `evaluation-cases.json` | Twenty-four labelled mutations |
| `evidence/manifest.json` | Reproducible subject-bound result digests and explicit limitations |
| `candidate/` | Unsafe direct-agent baseline |
| `reference/` | Governed handoff with explicit non-authorities |
| `workshop/starter/` | Learner decision package |
| `assets/` | Validated diagram specification and deterministic SVG renderer |

## Expected boundary

The reference state is `READY_FOR_INTEGRATION_REVIEW`. The lab deliberately reports all of the following as false:

- merge authorized;
- deployment authorized;
- legacy retirement authorized; and
- business outcome proven.

Those are separate decisions made by trusted organizational systems and accountable people.

## Optional production extension

Replace the deterministic proposal provider with a model only after defining a representative evaluation population, model/data identities, privacy boundaries, failure behavior, cost and latency targets, human-review UX, and ongoing monitoring. The trusted application must still own authorization, evidence selection, persistence, idempotency, and protected effects.
