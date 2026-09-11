const REPO = 'https://github.com/mahsa-teimourikia/spec-driven-development';

const availableLesson = {
  id: 'c01', course: 1, level: 'beginner', part: 'I · SDD foundations', status: 'available',
  title: 'Why agentic coding changes the PDLC',
  summary: 'Model agentic delivery as an enterprise control loop: durable intent, bounded autonomy, enforceable policy, human authority, and auditable evidence.',
  outcomes: [
    'Explain why the constraint, review, and evidence bottlenecks move when implementation becomes cheap.',
    'Discover distributed requirements, evaluate applicability, and preserve owner/version/source provenance.',
    'Run unsafe and governed candidate code through specification, policy, architecture, test, traceability, review, and approval gates.',
    'Produce an evidence bundle, identify residual risk, and choose a delivery workflow in proportion to impact.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/agentic_pdlc.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py`,
  repoLab: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/northstar-underwriter`,
  run: 'python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py',
  runRepo: 'python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py --candidate all',
  references: [
    ['GitHub Spec Kit: Agentic SDD', 'https://github.github.com/spec-kit/reference/agentic-sdd.html'],
    ['NIST Secure Software Development Framework', 'https://csrc.nist.gov/pubs/sp/800/218/final'],
    ['DORA 2025 report', 'https://dora.dev/research/ai/gen-ai-report/dora-impact-of-generative-ai-in-software-development.pdf']
  ],
  checkpoint: {
    question: 'A privacy rule applies to confidential data, but JIRA-4821 does not state the data classification. What should the control plane do?',
    options: [
      'Mark applicability uncertain and stop for clarification before implementation.',
      'Treat the privacy rule as not applicable because the ticket omitted the field.',
      'Let the coding agent infer the classification from its proposed architecture.'
    ],
    answer: 0,
    explanation: 'Missing applicability evidence is not evidence that a policy does not apply. The control plane must fail closed, obtain an authoritative classification, and record the decision.'
  }
};

function planned(course, level, part, title, summary) {
  return {
    id: `c${String(course).padStart(2, '0')}`, course, level, part,
    status: 'planned', title, summary,
    outcomes: ['Outcomes will be published with the complete chapter, notebook, lab, checkpoint, and evidence package.'],
    readme: null, notebook: null, lab: null, repoLab: null, repoFixture: null,
    references: [['Course plan', `${REPO}/blob/main/COURSE_PLAN.md`]], checkpoint: null
  };
}

const LESSONS = [
  availableLesson,
  planned(2, 'beginner', 'I · SDD foundations', 'Specs vs prompts vs requirements vs design', 'Separate transient instructions, obligations, solution choices, and durable sources of truth.'),
  planned(3, 'beginner', 'I · SDD foundations', 'The specification hierarchy', 'Connect organization intent to platform, domain, project, feature, and implementation constraints.'),
  planned(4, 'beginner', 'I · SDD foundations', 'Company vs project vs feature requirements', 'Resolve scope, ownership, inheritance, specialization, and conflicts across levels.'),
  planned(5, 'beginner', 'II · Executable specifications', 'Requirements engineering for agents', 'Discover assumptions and express requirements that constrain agent action.'),
  planned(6, 'beginner', 'II · Executable specifications', 'User stories, EARS, SHALL requirements, and scenarios', 'Use complementary requirement forms without mistaking syntax for quality.'),
  planned(7, 'beginner', 'II · Executable specifications', 'Acceptance criteria and invariants', 'Define examples and properties that produce meaningful conformance evidence.'),
  planned(8, 'beginner', 'II · Executable specifications', 'Non-functional requirements', 'Make security, reliability, performance, accessibility, and operability measurable.'),
  planned(9, 'beginner', 'II · Executable specifications', 'Architecture Decision Records', 'Capture consequential decisions, alternatives, rationale, and consequences.'),
  planned(10, 'beginner', 'II · Executable specifications', 'Requirement traceability', 'Link intent through design, tasks, code, tests, approvals, and operational evidence.'),
  planned(11, 'intermediate', 'III · SDD frameworks', 'GitHub Spec Kit', 'Use constitution, clarification, planning, checks, analysis, implementation, and convergence.'),
  planned(12, 'intermediate', 'III · SDD frameworks', 'OpenSpec', 'Manage current specifications and explicit change deltas for brownfield work.'),
  planned(13, 'intermediate', 'III · SDD frameworks', 'Kiro Specs', 'Apply feature, bug-fix, and quick-spec workflows with appropriate approval depth.'),
  planned(14, 'intermediate', 'III · SDD frameworks', 'Agent instructions such as AGENTS.md', 'Make repository-local operating guidance discoverable and maintainable.'),
  planned(15, 'intermediate', 'III · SDD frameworks', 'Comparing and choosing frameworks', 'Select a process harness using risk, lifecycle, integration, and governance criteria.'),
  planned(16, 'intermediate', 'III · SDD frameworks', 'Custom enterprise extensions', 'Extend workflows with organizational templates, policies, evidence, and exception paths.'),
  planned(17, 'intermediate', 'IV · Agentic PDLC', 'Idea → discovery → spec → design → implementation', 'Build an end-to-end flow with explicit state, owners, gates, and handoffs.'),
  planned(18, 'intermediate', 'IV · Agentic PDLC', 'Brownfield development', 'Recover system truth before changing code with incomplete or stale specifications.'),
  planned(19, 'intermediate', 'IV · Agentic PDLC', 'Bug fixes and small changes', 'Use a proportional workflow that preserves evidence without process theatre.'),
  planned(20, 'intermediate', 'IV · Agentic PDLC', 'Multi-repository development', 'Coordinate contracts, versions, sequencing, and ownership across repositories.'),
  planned(21, 'intermediate', 'IV · Agentic PDLC', 'Parallel agents', 'Partition work by contracts and boundaries while controlling integration risk.'),
  planned(22, 'intermediate', 'IV · Agentic PDLC', 'PR and review strategy', 'Design changes and evidence so humans can review agent output efficiently.'),
  planned(23, 'intermediate', 'IV · Agentic PDLC', 'Human approval gates', 'Place accountable decisions at risk-bearing transitions without becoming a bottleneck.'),
  planned(24, 'advanced', 'V · Enterprise controls', 'Security and privacy', 'Translate threat, data, identity, and privacy obligations into preventive and detective controls.'),
  planned(25, 'advanced', 'V · Enterprise controls', 'AI governance', 'Govern model use, data exposure, accountability, evaluation, and exceptions.'),
  planned(26, 'advanced', 'V · Enterprise controls', 'Architecture governance', 'Encode principles and fitness functions while preserving documented exceptions.'),
  planned(27, 'advanced', 'V · Enterprise controls', 'Testing and quality', 'Build layered evidence for generated changes and the specifications that direct them.'),
  planned(28, 'advanced', 'V · Enterprise controls', 'Observability', 'Specify telemetry and feedback needed to verify behavior after deployment.'),
  planned(29, 'advanced', 'V · Enterprise controls', 'Compliance', 'Map obligations to controls, evidence, retention, approvals, and audit narratives.'),
  planned(30, 'advanced', 'V · Enterprise controls', 'Supply-chain controls', 'Constrain dependencies, provenance, builds, artifacts, and deployment authority.'),
  planned(31, 'advanced', 'V · Enterprise controls', 'CI/CD enforcement', 'Turn policy and evidence requirements into automated delivery gates.'),
  planned(32, 'advanced', 'VI · Advanced agentic SDD', 'Agent context engineering', 'Assemble relevant, authoritative, minimal context for reliable agent decisions.'),
  planned(33, 'advanced', 'VI · Advanced agentic SDD', 'Specification decomposition', 'Split intent along stable interfaces while preserving end-to-end properties.'),
  planned(34, 'advanced', 'VI · Advanced agentic SDD', 'Context compression', 'Reduce context without losing obligations, decisions, provenance, or unresolved risk.'),
  planned(35, 'advanced', 'VI · Advanced agentic SDD', 'Multi-agent orchestration', 'Coordinate roles, state, handoffs, conflicts, budgets, and convergence.'),
  planned(36, 'advanced', 'VI · Advanced agentic SDD', 'Spec drift', 'Detect and reconcile divergence among intent, artifacts, implementation, and reality.'),
  planned(37, 'advanced', 'VI · Advanced agentic SDD', 'Continuous specification', 'Evolve specifications as monitored, versioned operational assets.'),
  planned(38, 'advanced', 'VI · Advanced agentic SDD', 'Specification-driven evaluation', 'Evaluate agents against requirements, constraints, traces, and business outcomes.'),
  {
    ...planned(39, 'enterprise', 'Enterprise Agent capstone', 'Design a real enterprise Agentic PDLC', 'Integrate the hierarchy, workflows, controls, evidence, exceptions, and rollout plan for a realistic enterprise.'),
    id: 'capstone', course: 'Capstone'
  }
];
