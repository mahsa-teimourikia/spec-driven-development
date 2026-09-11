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
  }
];
