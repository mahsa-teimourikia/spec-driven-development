# AI-2219 production-readiness workshop

Northstar Mutual is moving the Course 06–07 broker-response capability from a controlled pilot toward Commercial Underwriting. The functional behavior and its bounded evidence portfolio already exist. Your task is to specify the production qualities that determine whether the system can operate safely, reliably, efficiently, and economically.

## Start here

1. Read the deliberately inadequate [rollout ticket](ticket/AI-2219-rollout.md).
2. Inspect [W1–W3](workload-profiles.json), but treat W2 and W3 as unresolved planning hypotheses.
3. Complete the [starter workshop](workshop/starter/README.md) without inventing targets.
4. Run the deterministic lab from the repository root:

   ```bash
   python3 curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py
   ```

5. Compare your decisions with the [reference NFR contract](reference/nfr-contract.json), [measurement plan](reference/measurement-plan.json), [degradation policy](reference/degradation-policy.json), [agent budget](reference/agent-budget.json), and [traceability](reference/traceability.csv).

## Evidence boundary

The runtime events, quality cases, workload figures, and owner decisions are fictional teaching fixtures. They exercise percentile, ratio, slice, cost-denominator, retry, budget, and gating mechanics. They are not production telemetry, live-model results, load-test evidence, contractual SLAs, or authorization to deploy.

The reference package intentionally leaves the cost and AI-quality targets unresolved and capacity unmeasured. A mature NFR process can preserve useful measurements while still returning `BLOCKED` or `NOT_MEASURED`.

## What good work looks like

- every requirement identifies its characteristic, population, measurement method, unit, window, owner, target state, evidence method, and failure response;
- approved numeric targets trace to explicit owner decisions and evidence IDs;
- unresolved targets remain `null`, never guessed from phrases such as “fast” or “cost-effective”;
- semantic good events distinguish valid service and approved graceful degradation from error envelopes;
- latency states start/end boundaries and workload;
- reliability, quality, and cost preserve numerators and denominators;
- model-provider failure, policy failure, and telemetry failure do not silently weaken authorization or mutation controls;
- retries, tool calls, model turns, tokens, and side effects are bounded by trusted application code; and
- production readiness remains blocked until real load, telemetry, representative evaluation, quota, and owner evidence exist.
