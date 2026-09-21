# Starter — write the production-quality contract

Do not begin by choosing numbers. Begin by defining measurement semantics and identifying who has authority to approve a target.

1. Replace every `TODO` in `nfr-contract.json` with a characteristic, population, measurement, target state, owner, evidence method, and failure response.
2. Record discovered or requested target decisions in `target-decisions.json`. Keep values `null` where authority or evidence is absent.
3. Complete `measurement-plan.json` with signals, aggregation, producer, retention owner, content policy, and limitations.
4. Define dependency-specific failure modes in `degradation-policy.json`. Degradation must reduce autonomy rather than remove a control.
5. Add execution and side-effect limits to `agent-budget.json` and define budget-exhaustion behavior.
6. Link each NFR to its workload/population, measurement, decision, evidence, and response owner in `traceability.csv`.

Before comparing with the reference, explain:

- why a synthetic p95 is not a production SLO result;
- why `HTTP 200` with an error body is not necessarily a good event;
- why cost per API call is weaker than cost per successful compliant workflow;
- why provider throttling must not create a retry storm;
- why policy or authorization failure cannot trigger fail-open automation; and
- which targets remain unresolved and who must decide them.
