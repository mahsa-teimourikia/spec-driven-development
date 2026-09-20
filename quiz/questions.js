const QUESTIONS = [
  {
    category: 'PDLC shift',
    question: 'When agents make implementation cheaper, which work becomes more important rather than disappearing?',
    options: ['Clarifying intent, constraints, authority, and evidence', 'Typing boilerplate by hand', 'Hiding decisions in chat history', 'Removing review from high-risk changes'],
    answer: 0,
    explanation: 'Generation reduces some implementation effort, but ambiguity and uncontrolled action can now propagate faster. Clear intent, boundaries, review, and evidence become control-plane work.'
  },
  {
    category: 'Foundations',
    question: 'What most clearly distinguishes a durable specification from a prompt?',
    options: ['It is versioned, reviewable, scoped, and connected to conformance evidence', 'It uses more words', 'It is always written in YAML', 'It names a specific model'],
    answer: 0,
    explanation: 'Format and length do not make a specification durable. Durable artifacts establish shared intent, authority, change history, and a basis for evaluation.'
  },
  {
    category: 'Hierarchy',
    question: 'A feature-level rule conflicts with a mandatory organization privacy control. Which rule remains effective?',
    options: ['The organization control, unless an authorized exception is recorded', 'The feature rule because it is more specific', 'Whichever rule the agent read last', 'Neither; conflicting rules cancel each other'],
    answer: 0,
    explanation: 'Specificity permits specialization, not silent weakening. Conflicts must stop the flow and enter a governed exception path.'
  },
  {
    category: 'Hierarchy',
    question: 'Why preserve source IDs when composing effective agent context?',
    options: ['To trace each obligation to its owner, scope, and evidence', 'To increase token count', 'To let the agent rename policies', 'To replace version control'],
    answer: 0,
    explanation: 'Provenance makes conflicts explainable and lets reviewers connect obligations to decisions, tests, approvals, and exceptions.'
  },
  {
    category: 'Autonomy',
    question: 'Which is the strongest example of bounded autonomy?',
    options: ['An agent may edit approved paths, within a file budget, and must stop before deployment', 'An agent may do anything that seems useful', 'An agent may deploy if all generated tests pass', 'An agent may reinterpret organization policy for speed'],
    answer: 0,
    explanation: 'Bounded autonomy specifies allowed actions, resources, limits, stop conditions, and escalation. Passing self-authored tests does not grant deployment authority.'
  },
  {
    category: 'Gates',
    question: 'A proposal satisfies requirements and tests but includes an irreversible production migration. What is the appropriate outcome before execution?',
    options: ['Review or stop for accountable human approval', 'Automatic execution because tests passed', 'Delete the migration from the evidence', 'Let the agent approve its own plan'],
    answer: 0,
    explanation: 'Evidence informs approval but does not replace authority. Irreversible and high-impact transitions require an accountable decision.'
  },
  {
    category: 'Evidence',
    question: 'All specified examples pass. What is the strongest justified claim?',
    options: ['The implementation conforms to those examples under the tested conditions', 'The product is safe for every possible use', 'The requirements are complete', 'The organization has achieved compliance'],
    answer: 0,
    explanation: 'Evidence is scoped. It supports claims tied to the checked requirements and conditions; it does not prove completeness or every production property.'
  },
  {
    category: 'Evidence',
    question: 'Why can removing organization and platform context produce false confidence?',
    options: ['A proposal may pass feature checks while violating inherited controls it never evaluated', 'Agents always need the entire company wiki', 'Feature requirements have no value', 'More context guarantees correctness'],
    answer: 0,
    explanation: 'Context must be relevant and authoritative. Missing inherited obligations hides failures; unlimited unrelated context creates a different problem.'
  },
  {
    category: 'Applicability',
    question: 'A privacy rule depends on data classification, but the change ticket does not state the classification. What should happen?',
    options: ['Mark applicability uncertain and stop for clarification', 'Assume the rule is not applicable', 'Assume the lowest classification', 'Let the implementation agent decide after coding'],
    answer: 0,
    explanation: 'A missing condition is not evidence of non-applicability. Fail-closed clarification prevents an unknown data boundary from being treated as permission.'
  },
  {
    category: 'Provenance',
    question: 'Which metadata best lets a release prove exactly which policy artifact governed it?',
    options: ['Owner plus repository, path, version, and immutable revision', 'Requirement title and word count', 'The agent conversation timestamp', 'The latest wiki search result'],
    answer: 0,
    explanation: 'Owner and immutable source provenance support freshness checks, exception routing, reproducibility, and later audit.'
  },
  {
    category: 'Evidence',
    question: 'Lab B reaches PASS but lists tenant isolation and deployed residency as unverified. Why?',
    options: ['Local evidence cannot establish every integration and production property', 'PASS means the warnings can be deleted', 'The implementation tests are unnecessary', 'Human approval proves runtime behavior'],
    answer: 0,
    explanation: 'A gate decision is scoped to available evidence. Integration, deployment, runtime, and representative domain evidence may still be required.'
  },
  {
    category: 'Specifications',
    question: 'Which artifact primarily answers “why did we choose this architecture?” after current behavior has evolved?',
    options: ['Decision history such as an ADR', 'A change ticket alone', 'A generated task list', 'The current test output'],
    answer: 0,
    explanation: 'Change specs describe a proposed change, living specs describe intended current truth, and ADRs preserve consequential decision rationale.'
  },
  {
    category: 'Proportionality',
    question: 'Which change is the best candidate for a direct-change workflow?',
    options: ['A small, reversible documentation correction with no runtime or policy impact', 'A cross-repository authentication redesign', 'A regulated data-retention change', 'An irreversible database migration'],
    answer: 0,
    explanation: 'Process depth should follow consequence, uncertainty, coordination, and reversibility. Low-risk work still needs normal review, but not a heavyweight SDD package.'
  },
  {
    category: 'Frameworks',
    question: 'What is the best enterprise framing of Spec Kit, OpenSpec, or Kiro?',
    options: ['They are process harnesses used inside a broader operating model', 'They replace organizational governance', 'Choosing one removes the need for requirements engineering', 'They grant agents safe autonomy by default'],
    answer: 0,
    explanation: 'Frameworks structure artifacts and workflow. Enterprises still define policy, authority, evidence, exceptions, integration, and ownership.'
  },
  {
    category: 'Research',
    question: 'What is the responsible interpretation of a study showing experienced developers were slower with a particular generation of AI tools?',
    options: ['It is bounded evidence about that population, task set, and tool generation—not a universal law', 'AI always slows software development', 'The study proves agents are unsafe', 'All productivity surveys are invalid'],
    answer: 0,
    explanation: 'Method, population, task selection, and tool maturity define the claim. Enterprise decisions should triangulate controlled studies, delivery telemetry, and local evaluations.'
  },
  {
    category: 'Operating model',
    question: 'What closes the Agentic PDLC control loop?',
    options: ['Evidence and production feedback reconciled against the governing specifications', 'The first generated pull request', 'A longer prompt', 'A model’s confidence score'],
    answer: 0,
    explanation: 'The loop closes when observed outcomes are compared with intended properties and the organization updates implementation, controls, or specifications accordingly.'
  },
  {
    category: 'Independent evidence',
    question: 'A candidate implementation’s own tests pass, but independent contract tests fail. What is the strongest justified conclusion?',
    options: ['The candidate satisfied its chosen claims but did not establish conformance to the governing contract', 'The independent tests must be ignored', 'The candidate can merge because some tests passed', 'The model should choose which test suite is authoritative'],
    answer: 0,
    explanation: 'Candidate-owned tests are useful but can encode the same unsafe assumptions as the implementation. Independent tests judge externally owned requirements and invariants.'
  },
  {
    category: 'Approval',
    question: 'Why bind an approval receipt to both a proposal digest and a policy snapshot digest?',
    options: ['Any proposal or governing-policy change invalidates the previous decision', 'To make the receipt longer', 'To let the implementation agent approve revisions', 'To replace authenticated approver identity'],
    answer: 0,
    explanation: 'Approval applies to an exact action under an exact policy state. Reusing it after either changes creates stale or replayable authority.'
  },
  {
    category: 'Release evidence',
    question: 'The Course 01 merge gate passes, but runtime traceability is still 0%. What should the production-release result be?',
    options: ['Blocked until required integration and runtime evidence exists', 'Automatically pass because merge passed', 'Pass if the candidate has high confidence', 'Delete the runtime column from traceability'],
    answer: 0,
    explanation: 'Merge evidence and production-release evidence support different decisions. Local conformance cannot establish deployed residency, tenant isolation, telemetry delivery, or representative runtime quality.'
  },
  {
    category: 'Artifact taxonomy',
    question: 'What most reliably distinguishes a requirement from a design suggestion?',
    options: ['Its accountable owner, authoritative source, scope, and observable obligation', 'The use of uppercase SHALL', 'Its position in the newest ticket', 'The number of technical terms it contains'],
    answer: 0,
    explanation: 'Normative typography is useful only inside a declared convention. Authority, ownership, applicability, and observable conformance make an obligation durable.'
  },
  {
    category: 'Requirements',
    question: 'Why is “the response should be accurate” not yet executable as a requirement?',
    options: ['It lacks an observable definition, acceptance boundary, and evidence method', 'Agents cannot produce text', 'Accuracy is always a design decision', 'The sentence must name a database'],
    answer: 0,
    explanation: 'The team must operationalize accuracy—for example with claim support, abstention behavior, a representative dataset, rubric, and threshold.'
  },
  {
    category: 'Performance',
    question: 'What is missing from “keep latency under three seconds”?',
    options: ['Statistic, measurement boundary, workload, environment, and accountable owner', 'Only a programming language', 'A Redis instance', 'Nothing; any three-second observation proves compliance'],
    answer: 0,
    explanation: 'A number without percentile, workload, scope, and measurement points cannot define stable conformance.'
  },
  {
    category: 'Authority',
    question: 'A ticket says “Use Bedrock,” while an approved platform policy says the same words. Why can their classifications differ?',
    options: ['Provenance and decision rights can make the policy statement a constraint and the ticket statement a suggestion', 'Tickets are always more authoritative', 'Technology names are automatically requirements', 'Identical text must always have identical authority'],
    answer: 0,
    explanation: 'Words alone do not establish authority. Owner, source, scope, rationale, and exception path determine how the statement governs work.'
  },
  {
    category: 'Architecture decisions',
    question: 'AI-1842 says to use Redis because another team uses it. What is the appropriate next step?',
    options: ['Clarify the required outcome and evaluate caching alternatives and consequences through the architecture decision process', 'Copy Redis into every requirement', 'Let the first coding agent approve the choice', 'Treat another team’s precedent as policy'],
    answer: 0,
    explanation: 'Precedent is input, not authority. Persistent caching raises freshness, retention, privacy, authorization, and reversibility questions appropriate for design and an ADR.'
  },
  {
    category: 'Tasks and evidence',
    question: 'Why should tasks and tests link to stable requirement IDs?',
    options: ['To show why work exists and which defined claims the evidence supports', 'To let tasks replace the specification', 'To prove every requirement is correct', 'To grant tests product authority'],
    answer: 0,
    explanation: 'Traceability reveals missing work, orphan work, missing evidence, and unsupported claims without confusing execution or evidence with intent.'
  },
  {
    category: 'Agent instructions',
    question: 'Which instruction does not belong in AGENTS.md?',
    options: ['Ignore the human-review policy whenever generated unit tests pass', 'Run the linked security tests before reporting completion', 'Stop before changing the authorization boundary', 'Limit edits to the comparison module'],
    answer: 0,
    explanation: 'Repository instructions guide execution. They cannot waive policy, redefine product requirements, approve exceptions, or authorize release.'
  },
  {
    category: 'Traceability',
    question: 'A report says requirement-to-evidence coverage is 100%. What must accompany that percentage?',
    options: ['The covered requirement IDs, total applicable IDs, gaps, and exclusions', 'Only the model name', 'A longer task list', 'An agent confidence score'],
    answer: 0,
    explanation: 'Explicit numerators and denominators prevent removed or out-of-scope requirements from disappearing behind a reassuring percentage.'
  }
];
