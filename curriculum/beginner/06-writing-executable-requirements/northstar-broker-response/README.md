# AI-2219 workshop — Broker response processing

Turn the intentionally dangerous [product ticket](ticket/AI-2219.md) into a connected set of
requirements, decision rules, scenarios, contracts, states, and evidence without granting the model
authority to mutate underwriting records.

## Your assignment

1. Read the ticket and the three versioned sources.
2. Complete every `TODO` in [`workshop/starter`](workshop/starter/README.md).
3. Make artifact roles explicit: normative requirement, normative elaboration, normative example,
   informative explanation, or evidence.
4. Run the Course 06 lab and focused tests.
5. Inject a decision-table contradiction and verify that the workflow stops rather than choosing a
   convenient artifact.
6. Compare with [`reference`](reference/) only after you can defend each relationship and boundary.

## Expected release boundary

Extraction, deterministic classification, and proposal creation are ready. Applying an unverified
value remains review-required while `OQ-BR-001` is open. A reviewed conflict replacement requires
exact resolution authority; automatic replacement of a verified conflicting value is prohibited.
These are capability states, not percentages.

## Evidence boundary

The fixture uses eleven synthetic labelled cases and an in-memory update. It evaluates deterministic
decisions after extraction; it neither evaluates a language model nor proves authenticated owner
approval, production transactions, or runtime control effectiveness.
