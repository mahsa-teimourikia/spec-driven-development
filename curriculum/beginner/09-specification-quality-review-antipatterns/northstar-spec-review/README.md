# AI-2290 specification review workshop

Northstar’s team believes the AI-2290 specification is complete because it mentions AI, performance, security, scalability, human review, enterprise policy, and tests. Your job is to determine whether those words establish an implementation-ready contract.

## Learner path

1. Read the [unsafe ticket](ticket/AI-2290.md).
2. Inspect the candidate [review input](candidate/review-input.json), [autonomy contract](candidate/autonomy-contract.json), [traceability](candidate/traceability.json), [evidence](candidate/evidence.json), and [context manifest](candidate/context-manifest.json).
3. Review the Course 03-style [resolved policy expectation](resolved-policy-expectation.json), [35-case anti-pattern portfolio](evaluation-cases.json), and [capability-scoped readiness fixture](capability-readiness.json). These extend AI-2290 through authority conflict, self-confirming loops, execution safety, brownfield reconciliation, migration, rollout, fallback, observability, and production-claim boundaries.
4. Complete the [starter review](workshop/starter/README.md) before consulting the reference.
5. Run:

   ```bash
   python3 curriculum/beginner/09-specification-quality-review-antipatterns/lab.py
   ```

6. Compare your results with the reference [review report](reference/review-report.json), [repair plan](reference/repair-plan.md), [readiness decision](reference/readiness-decision.json), and repaired package.

## Evidence boundary

All people, policies, revisions, findings, digests, evidence, and decisions are fictional training fixtures. Readiness booleans and their linked evidence IDs are synthetic assertions, not authenticated attestations. The deterministic rules cover labelled anti-patterns; they are not a general semantic reviewer, an owner approval, implementation evidence, or a production-readiness assessment.

The lexical baseline finds 7/7 responsible-sounding concepts and still misses the dangerous semantics. The governed review produces typed findings, seven human remediation clusters, and a `STOP`, not a score. The repaired `reviewed_by` links prove review coverage only: conformance coverage remains 0/10 until implementation evidence exists. The extended portfolio matches 35/35 transparent labelled cases; that is fixture rule coverage, not general reviewer accuracy. Capability readiness permits four bounded work areas while automatic mutation remains blocked. Production release remains outside this course’s authority.
