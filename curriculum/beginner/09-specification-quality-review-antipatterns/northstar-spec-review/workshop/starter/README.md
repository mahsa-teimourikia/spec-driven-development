# Starter — review AI-2290 before implementation

1. Read the unsafe ticket and every candidate artifact.
2. Complete `review-findings.json` with evidence-backed findings across correctness, completeness, clarity, consistency, verifiability, traceability, authority, maintainability, autonomy, and decision ownership.
3. Use only `blocking`, `review`, or `informational` severity. Do not invent a composite score.
4. Complete `readiness-decision.json`. Blocking findings affecting automatic mutation must stop that capability.
5. Propose repairs at the owning source. Do not patch generated context or self-authorize product, policy, architecture, exception, or release decisions.
6. Run the Course 09 lab and compare your work with the reference only after documenting the evidence for every finding.
7. Select one extended evaluation case in each family—authority, controls, execution safety, brownfield transition, and operability—and explain why its severity is proportionate.
8. Complete a capability-scoped readiness table. Do not let an automatic-mutation blocker stop independent analysis work or disappear into a project-level READY status.

Your review is a proposal for accountable owners. It is not itself permission to implement or deploy.
