# Northstar broker-export hierarchy workshop

This fictional workshop turns ticket `AI-1937` into an effective specification.
The learner must not concatenate every nearby document or let the most specific
sentence win automatically.

## Workflow

1. Read [`ticket/AI-1937.md`](ticket/AI-1937.md) and inspect the evidence-backed
   [`ticket/change-context.json`](ticket/change-context.json).
2. Review every record under [`catalog/`](catalog/) without assuming it applies.
3. Complete the templates in [`workshop/starter/`](workshop/starter/).
4. Run the deterministic resolver:

   ```bash
   python3 curriculum/beginner/03-the-specification-hierarchy/lab.py
   ```

5. Remove `EXC-009` from the resolver call and explain why implementation stops.
6. Remove the data-classification fact and explain why `unknown` is not `N/A`.
7. Compare your work with [`reference/`](reference/) only after committing to
   your decisions.

The reference package is a teaching resolution, not a real legal, privacy, or
records decision. `APR-EXC-009-TRAINING` is a fixture locator, not proof of an
authenticated approval.

## Expected outcome

The reference run evaluates 13 candidate requirements: 11 are applicable, two
are not applicable, and none are uncertain. It composes eight effective controls,
records one authority-based precedence decision, applies one scoped exception,
and reaches `READY`. Removing or expiring the exception exposes a genuine
mandatory-policy conflict and changes the gate to `STOP`.
