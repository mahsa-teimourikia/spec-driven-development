const REPO = 'https://github.com/mahsa-teimourikia/spec-driven-development';

const course01 = {
  id: 'c01', course: 1, level: 'beginner', part: 'I · SDD foundations', status: 'available',
  title: 'Why agentic coding changes the PDLC',
  summary: 'Turn a deficient enterprise ticket into a governed change package, review competing agent implementations, and separate merge evidence from production authority.',
  outcomes: [
    'Explain why the constraint, review, and evidence bottlenecks move when implementation becomes cheap.',
    'Discover distributed requirements, evaluate applicability, preserve provenance, and record ticket-versus-policy conflicts.',
    'Write clarifications, requirements, design, tasks, and design-to-runtime traceability before delegating implementation.',
    'Contrast passing candidate-owned tests with independent tests and labelled evaluation evidence.',
    'Verify proposal-bound approval receipts and separate merge PASS from a still-blocked production release.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/agentic_pdlc.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py`,
  repoLab: `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/northstar-underwriter`,
  run: 'python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py',
  runRepo: 'python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py --candidate all',
  labs: [
    {
      title: 'Lab A — Simulate the control plane',
      description: 'Inspect typed requirements, conflicts, bounded proposals, evidence coverage, and proportional workflow routing.',
      command: 'python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py',
      links: [['View Lab A', `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/agentic_pdlc.ipynb`]]
    },
    {
      title: 'Lab B — Make the enterprise decisions',
      description: 'Triage a deficient ticket, author the change package, compare candidate-owned with independent evidence, verify bound approvals, and separate merge from release.',
      command: 'python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py --candidate all',
      links: [['View Lab B runner', `${REPO}/blob/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py`], ['Explore the repository fixture', `${REPO}/tree/main/curriculum/beginner/01-why-agentic-coding-changes-pdlc/northstar-underwriter`]]
    }
  ],
  references: [
    ['GitHub Spec Kit: Agentic SDD', 'https://github.github.com/spec-kit/reference/agentic-sdd.html'],
    ['NIST Secure Software Development Framework', 'https://csrc.nist.gov/pubs/sp/800/218/final'],
    ['DORA 2025 report', 'https://dora.dev/research/ai/gen-ai-report/dora-impact-of-generative-ai-in-software-development.pdf']
  ],
  checkpoint: {
    question: 'The unsafe candidate’s own tests pass, but independent tests and policy gates fail. What is the correct merge decision?',
    options: [
      'STOP; candidate-owned tests establish only the candidate’s chosen claims.',
      'PASS; any passing test suite is sufficient evidence.',
      'REVIEW only if the coding agent reports low confidence.'
    ],
    answer: 0,
    explanation: 'Self-authored checks can confirm an unsafe design. Independent tests, policy, architecture, evaluation, traceability, and approval gates judge the change against external obligations.'
  }
};

const course02 = {
  id: 'c02', course: 2, level: 'beginner', part: 'I · SDD foundations', status: 'available',
  title: 'From prompt to executable specification',
  summary: 'Classify a mixed-authority enterprise request, repair ambiguous obligations, route consequential decisions, and validate a traceable artifact stack before an agent writes code.',
  outcomes: [
    'Classify prompts, intent, requirements, constraints, designs, ADRs, tasks, evidence, and agent instructions by purpose and authority.',
    'Replace vague quality claims with observable requirements, scenarios, measurement context, and accountable owners.',
    'Distinguish authoritative constraints from design suggestions even when the words are identical.',
    'Route reversible implementation choices, consequential architecture decisions, policy questions, and exceptions appropriately.',
    'Distinguish planned traceability from implemented, executed, passed, approved, and production-observed evidence.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/02-from-prompt-to-executable-specification/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/02-from-prompt-to-executable-specification/artifact_taxonomy.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/02-from-prompt-to-executable-specification/lab.py`,
  labs: [
    {
      title: 'Lab A — Classify and validate the stack',
      description: 'Compare a keyword baseline with a labelled teaching heuristic, repair weak requirements, route decision rights, inject failures, and measure evidence lifecycle stages.',
      command: 'python3 curriculum/beginner/02-from-prompt-to-executable-specification/lab.py',
      links: [['View the lab', `${REPO}/blob/main/curriculum/beginner/02-from-prompt-to-executable-specification/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/02-from-prompt-to-executable-specification/artifact_taxonomy.ipynb`]]
    },
    {
      title: 'Lab B — Repair ticket AI-1842',
      description: 'Decompose a realistic policy-comparison request, compare three Bedrock sources with different authority, complete the starter artifacts, and inspect a staged evidence plan.',
      command: 'Open the ticket, sources, and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/02-from-prompt-to-executable-specification/northstar-policy-comparison`], ['Complete the authority exercise', `${REPO}/tree/main/curriculum/beginner/02-from-prompt-to-executable-specification/northstar-policy-comparison/authority-exercise`], ['Inspect the reference stack', `${REPO}/tree/main/curriculum/beginner/02-from-prompt-to-executable-specification/northstar-policy-comparison/reference`]]
    }
  ],
  references: [
    ['RFC 8174 normative keyword clarification', 'https://www.rfc-editor.org/rfc/rfc8174'],
    ['ISO/IEC/IEEE 29148', 'https://www.iso.org/standard/72089.html'],
    ['Documenting Architecture Decisions', 'https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions'],
    ['GitHub Spec Kit: Agentic SDD', 'https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md']
  ],
  checkpoint: {
    question: 'AI-1842 says “Use Redis because another team uses it.” What should happen before implementation?',
    options: [
      'Treat Redis as a design hypothesis and route consequential caching decisions through an ADR and the appropriate owners.',
      'Copy it into the requirements because the ticket is the newest document.',
      'Put it in AGENTS.md so the implementation agent can approve it.'
    ],
    answer: 0,
    explanation: 'Another team’s choice is not authority. First clarify the outcome and constraints; then evaluate cache boundaries, alternatives, and consequences through the engineering decision process.'
  }
};

const course03 = {
  id: 'c03', course: 3, level: 'beginner', part: 'I · SDD foundations', status: 'available',
  title: 'The specification hierarchy',
  summary: 'Resolve organization, platform, domain, project, and feature requirements into a provenance-preserving effective specification without giving an agent authority to hide uncertainty or settle policy conflicts.',
  outcomes: [
    'Model six specification layers as ownership and scope boundaries rather than a universal winner ladder.',
    'Evaluate applicability before precedence and preserve evidence for applicable, not-applicable, and uncertain decisions.',
    'Distinguish authority from specificity, proximity, recency, and structured format.',
    'Confirm that obligations govern the same resource and lifecycle event before declaring a genuine conflict.',
    'Detect incompatible same-resource obligations and stop for accountable owner resolution.',
    'Validate scoped, conditional, expiring exceptions that change only named obligations and scope.',
    'Compose context with requirement IDs, source locators, applicability evidence, exception conditions, and stop states.',
    'Measure candidate-discovery precision and recall separately from applicability accuracy.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/03-the-specification-hierarchy/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/03-the-specification-hierarchy/specification_hierarchy.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/03-the-specification-hierarchy/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/03-the-specification-hierarchy/northstar-broker-export`,
  run: 'python3 curriculum/beginner/03-the-specification-hierarchy/lab.py',
  labs: [
    {
      title: 'Lab A — Resolve the effective specification',
      description: 'Compare naive concatenation with applicability, lifecycle, authority, conflict, exception, and context-composition decisions; then inject missing facts and expired exceptions.',
      command: 'python3 curriculum/beginner/03-the-specification-hierarchy/lab.py',
      links: [['View the resolver', `${REPO}/blob/main/curriculum/beginner/03-the-specification-hierarchy/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/03-the-specification-hierarchy/specification_hierarchy.ipynb`]]
    },
    {
      title: 'Lab B — Govern broker export AI-1937',
      description: 'Complete an applicability matrix, conflict and precedence record, exception assessment, provenance manifest, and bounded agent context before consulting the reference artifacts.',
      command: 'Open the ticket, catalog, and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/03-the-specification-hierarchy/northstar-broker-export`], ['Complete the starter artifacts', `${REPO}/tree/main/curriculum/beginner/03-the-specification-hierarchy/northstar-broker-export/workshop/starter`], ['Inspect the reference resolution', `${REPO}/tree/main/curriculum/beginner/03-the-specification-hierarchy/northstar-broker-export/reference`]]
    }
  ],
  references: [
    ['NIST OSCAL', 'https://pages.nist.gov/OSCAL/'],
    ['Open Policy Agent documentation', 'https://www.openpolicyagent.org/docs'],
    ['Cedar Policy Language reference guide', 'https://docs.cedarpolicy.com/'],
    ['JSON Schema specification', 'https://json-schema.org/specification']
  ],
  checkpoint: {
    question: 'PRIV-018 depends on data classification, but AI-1937 has no classification evidence. What should the resolver do?',
    options: [
      'Return UNCERTAIN and stop for clarification.',
      'Mark the rule not applicable because no restricted data was declared.',
      'Let the implementation agent infer the lowest-risk classification.'
    ],
    answer: 0,
    explanation: 'Missing evidence is not evidence of a scope mismatch. Fail-closed uncertainty prevents an unknown data boundary from silently widening agent autonomy.'
  }
};

const course04 = {
  id: 'c04', course: 4, level: 'beginner', part: 'I · SDD foundations', status: 'available',
  title: 'Company vs project vs feature requirements',
  summary: 'Place requirements where decision authority belongs, specialize them without silent weakening, map machine enforcement, and propagate central changes to affected project and feature work.',
  outcomes: [
    'Place enterprise, domain, project, and feature requirements according to decision rights and scope.',
    'Distinguish requirement owners, consumers, implementation owners, and enforcement owners.',
    'Model versioned INHERITS, SPECIALIZES, IMPLEMENTS, EVIDENCES, EXCEPTS, and SUPERSEDES relationships.',
    'Reject project or feature specializations that widen an allowlist, lower a minimum, or disable a required control.',
    'Separate documentation from detective and preventive enforcement.',
    'Select authoritative sources through a compact project manifest instead of copying central policy.',
    'Trace direct and transitive impact when a central requirement version changes.',
    'Constrain coding-agent writes while preserving IDs, provenance, enforcement, exceptions, and stop states.',
    'Separate release reproducibility, runtime control effectiveness, delivery outcomes, and agent-behavior signals.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/04-company-project-feature-requirements/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/04-company-project-feature-requirements/requirement_ownership.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/04-company-project-feature-requirements/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/04-company-project-feature-requirements/northstar-renewal`,
  run: 'python3 curriculum/beginner/04-company-project-feature-requirements/lab.py',
  labs: [
    {
      title: 'Lab A — Resolve ownership and propagation',
      description: 'Discover version-pinned sources, validate typed relationships and monotonic specialization, distinguish machine enforcement from documentation, and trace a central-policy change.',
      command: 'python3 curriculum/beginner/04-company-project-feature-requirements/lab.py',
      links: [['View the resolver', `${REPO}/blob/main/curriculum/beginner/04-company-project-feature-requirements/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/04-company-project-feature-requirements/requirement_ownership.ipynb`]]
    },
    {
      title: 'Lab B — Govern renewal recommendations AI-2048',
      description: 'Complete requirement placement, RACI, relationship, enforcement, impact, and bounded-context artifacts before comparing them with the reference decisions.',
      command: 'Open the ticket and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/04-company-project-feature-requirements/northstar-renewal`], ['Complete the starter artifacts', `${REPO}/tree/main/curriculum/beginner/04-company-project-feature-requirements/northstar-renewal/workshop/starter`], ['Inspect the reference decisions', `${REPO}/tree/main/curriculum/beginner/04-company-project-feature-requirements/northstar-renewal/reference`]]
    }
  ],
  references: [
    ['NIST OSCAL profile layer', 'https://pages.nist.gov/OSCAL/learn/concepts/layer/control/profile/'],
    ['Open Policy Agent management APIs', 'https://www.openpolicyagent.org/docs/management-introduction'],
    ['Cedar policy language guide', 'https://docs.cedarpolicy.com/'],
    ['GitHub rulesets', 'https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets']
  ],
  checkpoint: {
    question: 'A feature owner adds human_review = false even though enterprise policy requires review. What should happen?',
    options: [
      'STOP: the feature weakens inherited policy and needs an independently approved, scoped exception.',
      'Accept it because feature requirements are closest to the code.',
      'Accept it whenever feature-owned tests pass.'
    ],
    answer: 0,
    explanation: 'Specificity and test coverage do not create authority. Normal specialization must preserve or strengthen the parent; an authorized weakening requires a first-class exception.'
  }
};

const course05 = {
  id: 'c05', course: 5, level: 'beginner', part: 'II · Executable specifications', status: 'available',
  title: 'Requirements engineering for coding agents',
  summary: 'Turn an ambiguous broker-follow-up request into source-backed requirements, capability-level gates, exact approval boundaries, and measurable evidence.',
  outcomes: [
    'Distinguish unknowns, ambiguities, conflicts, design questions, and policy decisions.',
    'Write singular, observable requirements with stable identity, owners, sources, states, and evidence methods.',
    'Block only the capability affected by an unresolved question while safe upstream work continues.',
    'Validate typed requirement-gap status, rule provenance, observation evidence, and exact draft correspondence.',
    'Separate requirement lifecycle approval, release applicability, and capability readiness.',
    'Bind approval to exact content, current context, broker authorization, expiry, and single-use state.',
    'Define epistemic outcomes, fail-closed behavior, bounded retries, and idempotency.',
    'Detect stale agent context, semantic changes, orphan tasks, and unimplemented requirements.',
    'Evaluate requirement-review rules with labelled cases and honest denominators and limitations.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/05-requirements-engineering-for-agents/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/05-requirements-engineering-for-agents/requirements_engineering.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/05-requirements-engineering-for-agents/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/05-requirements-engineering-for-agents/northstar-broker-follow-up`,
  run: 'python3 curriculum/beginner/05-requirements-engineering-for-agents/lab.py',
  labs: [
    {
      title: 'Lab A — Engineer and enforce requirements',
      description: 'Inspect weak language, validate structured requirements, gate capabilities, inject stale approval failures, measure correspondence, and trace implementation work.',
      command: 'python3 curriculum/beginner/05-requirements-engineering-for-agents/lab.py',
      links: [['View the requirements lab', `${REPO}/blob/main/curriculum/beginner/05-requirements-engineering-for-agents/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/05-requirements-engineering-for-agents/requirements_engineering.ipynb`]]
    },
    {
      title: 'Lab B — Bound AI-2176 safely',
      description: 'Turn a vague broker-follow-up ticket into an ambiguity register, typed requirements package, explicit failure matrix, and a review-only first release.',
      command: 'Open the ticket and starter package; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/05-requirements-engineering-for-agents/northstar-broker-follow-up`], ['Complete the starter package', `${REPO}/tree/main/curriculum/beginner/05-requirements-engineering-for-agents/northstar-broker-follow-up/workshop/starter`], ['Inspect the reference package', `${REPO}/tree/main/curriculum/beginner/05-requirements-engineering-for-agents/northstar-broker-follow-up/reference`]]
    }
  ],
  references: [
    ['ISO/IEC/IEEE 29148:2018', 'https://www.iso.org/standard/72089.html'],
    ['EARS requirements syntax paper', 'https://doi.org/10.1109/RE.2009.9'],
    ['RFC 2119 requirement levels', 'https://www.rfc-editor.org/info/rfc2119/'],
    ['GitHub Spec Kit agentic SDD reference', 'https://github.github.com/spec-kit/reference/agentic-sdd.html']
  ],
  checkpoint: {
    question: 'OQ-017 leaves automatic delivery authority unresolved. What should the team do?',
    options: [
      'Keep send disabled while allowing bounded analysis and drafting to proceed.',
      'Let the coding agent enable send for cases it calls simple.',
      'Block the entire project, including safe analysis work.'
    ],
    answer: 0,
    explanation: 'An unresolved question should block only the capability that depends on it. Analysis and drafting remain useful; external delivery needs accountable policy and enforceable preconditions.'
  }
};

const course06 = {
  id: 'c06', course: 6, level: 'beginner', part: 'II · Executable specifications', status: 'available',
  title: 'Writing executable requirements',
  summary: 'Connect EARS and SHALL requirements to decision tables, scenarios, contracts, guarded states, and evidence without letting model output authorize state changes.',
  outcomes: [
    'Keep user stories as intent while expressing bounded obligations with an explicit normative convention.',
    'Select ubiquitous, event-driven, state-driven, unwanted, optional, and complex EARS patterns.',
    'Add preconditions, postconditions, frame conditions, failure behavior, invariants, and properties.',
    'Make interacting facts complete and deterministic with a normative decision table.',
    'Use role-labelled scenarios as examples without allowing them to become shadow policy.',
    'Distinguish schema, semantic, context, authorization, policy, approval, and execution validation.',
    'Recompute model-proposed status in trusted code and enforce guarded state transitions.',
    'Stop on normative contradiction and report capability-scoped readiness with exact blockers.',
    'Separate extraction evaluation from governed-decision evaluation and trace semantic change impact.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/06-writing-executable-requirements/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/06-writing-executable-requirements/requirements_writing.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/06-writing-executable-requirements/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/06-writing-executable-requirements/northstar-broker-response`,
  run: 'python3 curriculum/beginner/06-writing-executable-requirements/lab.py',
  labs: [
    {
      title: 'Lab A — Execute the behavioral model',
      description: 'Lint requirement language, validate representation consistency, classify proposals with trusted facts, enforce guarded transitions, inject contradictions, and measure bounded evidence.',
      command: 'python3 curriculum/beginner/06-writing-executable-requirements/lab.py',
      links: [['View the behavior lab', `${REPO}/blob/main/curriculum/beginner/06-writing-executable-requirements/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/06-writing-executable-requirements/requirements_writing.ipynb`]]
    },
    {
      title: 'Lab B — Govern AI-2219 broker responses',
      description: 'Complete the EARS/SHALL requirements, glossary, decision table, scenarios, proposal schema, and guarded state model before comparing with the reference behavior.',
      command: 'Open the ticket and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/06-writing-executable-requirements/northstar-broker-response`], ['Complete the starter package', `${REPO}/tree/main/curriculum/beginner/06-writing-executable-requirements/northstar-broker-response/workshop/starter`], ['Inspect the reference package', `${REPO}/tree/main/curriculum/beginner/06-writing-executable-requirements/northstar-broker-response/reference`]]
    }
  ],
  references: [
    ['EARS requirements syntax paper', 'https://doi.org/10.1109/RE.2009.9'],
    ['RFC 8174 normative keyword clarification', 'https://www.rfc-editor.org/rfc/rfc8174'],
    ['Cucumber Gherkin reference', 'https://cucumber.io/docs/gherkin/reference/'],
    ['JSON Schema Draft 2020-12', 'https://json-schema.org/draft/2020-12']
  ],
  checkpoint: {
    question: 'The model labels a broker-provided value approved, but it conflicts with a verified submission value. What owns the result?',
    options: [
      'Trusted application rules recompute CONFLICTING and prohibit mutation.',
      'The model status because it arrived in typed JSON.',
      'The newest scenario even when it contradicts the normative requirement.'
    ],
    answer: 0,
    explanation: 'Typed output is still a proposal. Trusted validation, the normative decision table, authorization, and guarded transitions own the disposition; applicable normative contradictions must stop for review.'
  }
};

function planned(course, level, part, title, summary) {
  return {
    id: `c${String(course).padStart(2, '0')}`, course, level, part,
    status: 'planned', title, summary,
    outcomes: ['Outcomes will be published with the complete chapter, notebook, lab, checkpoint, and evidence package.'],
    readme: null, notebook: null, lab: null, repoLab: null, repoFixture: null, labs: [],
    references: [['Course plan', `${REPO}/blob/main/COURSE_PLAN.md`]], checkpoint: null
  };
}

const LESSONS = [
  course01,
  course02,
  course03,
  course04,
  course05,
  course06,
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
