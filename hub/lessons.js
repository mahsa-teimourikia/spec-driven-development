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
    'Route verified conflicts through review and bind any replacement to the exact proposal, current context, and selected resolution.',
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
      'Trusted rules recompute CONFLICTING, prohibit automatic mutation, and require an exact reviewed resolution before replacement.',
      'The model status because it arrived in typed JSON.',
      'The newest scenario even when it contradicts the normative requirement.'
    ],
    answer: 0,
    explanation: 'Typed output is still a proposal. Trusted validation and the normative decision table classify the conflict. Automatic or direct replacement is prohibited; any reviewed replacement needs an authorized receipt bound to the exact proposal, current context, and replace-value resolution.'
  }
};

const course07 = {
  id: 'c07', course: 7, level: 'beginner', part: 'II · Executable specifications', status: 'available',
  title: 'Acceptance criteria, invariants, and evidence',
  summary: 'Turn executable requirements into layered, provenance-bearing assurance while keeping measurements, owner thresholds, release authority, and runtime effectiveness distinct.',
  outcomes: [
    'Distinguish requirements, acceptance criteria, tests, evidence, and release decisions.',
    'Write positive, negative, boundary, failure, stale-context, security, and compatibility criteria with observable outcomes.',
    'Pair examples with invariants, frame conditions, table coverage, state checks, and bounded properties.',
    'Use seeded specification and code mutations to test evidence sensitivity without claiming complete correctness.',
    'Define AI evaluation populations, slices, label provenance, split controls, and explicit denominators.',
    'Validate evidence provenance, freshness, invalidation, independence, and limitations.',
    'Route unevaluated languages, modalities, and field classes away from automated processing.',
    'Keep measured quality separate from threshold ownership and release authority.',
    'Connect preventive evidence to runtime signals with a trustworthy applicable population.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/acceptance_evidence.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/northstar-broker-evidence`,
  run: 'python3 curriculum/beginner/07-acceptance-criteria-invariants-evidence/lab.py',
  labs: [
    {
      title: 'Lab A — Build the assurance portfolio',
      description: 'Execute criteria and properties, inspect structural coverage, kill seeded mutants, measure evaluation slices, validate evidence freshness, and apply owner-controlled gates.',
      command: 'python3 curriculum/beginner/07-acceptance-criteria-invariants-evidence/lab.py',
      links: [['View the evidence lab', `${REPO}/blob/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/acceptance_evidence.ipynb`]]
    },
    {
      title: 'Lab B — Govern AI-2219 release evidence',
      description: 'Repair a weak verification ticket, author an acceptance and evaluation contract, complete traceability and an evidence manifest, and preserve an unresolved threshold as a blocker.',
      command: 'Open the ticket and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/northstar-broker-evidence`], ['Complete the starter package', `${REPO}/tree/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/northstar-broker-evidence/workshop/starter`], ['Inspect the reference evidence bundle', `${REPO}/tree/main/curriculum/beginner/07-acceptance-criteria-invariants-evidence/northstar-broker-evidence/reference/evidence`]]
    }
  ],
  references: [
    ['Cucumber Gherkin reference', 'https://cucumber.io/docs/gherkin/reference/'],
    ['Hypothesis documentation', 'https://hypothesis.readthedocs.io/'],
    ['in-toto Attestation Framework', 'https://github.com/in-toto/attestation'],
    ['NIST AI Risk Management Framework', 'https://www.nist.gov/itl/ai-risk-management-framework']
  ],
  checkpoint: {
    question: 'The governed fixture scores 12/12, but the release threshold has no accountable owner. What should the gate do?',
    options: [
      'Block as THRESHOLD_NOT_AUTHORIZED while retaining the measurement and its limitations.',
      'Choose 95% because it is a common quality target.',
      'Release because a perfect fixture score proves production quality.'
    ],
    answer: 0,
    explanation: 'A measurement is evidence, not decision authority. The small synthetic fixture also cannot justify a production-quality claim; an accountable owner must approve the threshold and its risk rationale.'
  }
};

const course08 = {
  id: 'c08', course: 8, level: 'beginner', part: 'II · Executable specifications', status: 'available',
  title: 'Non-functional requirements for agentic systems',
  summary: 'Turn performance, reliability, resilience, security, privacy, observability, cost, capacity, and AI-quality expectations into owned, measurable contracts without inventing targets.',
  outcomes: [
    'Write NFRs with explicit populations, workload profiles, boundaries, units, statistics, windows, owners, evidence methods, and failure responses.',
    'Keep unresolved targets explicit and trace approved values to accountable owner decisions and evidence.',
    'Measure percentile latency with sample-size caveats; keep semantic service success separate from control-compliant success; and preserve privacy, quality, and cost denominators.',
    'Distinguish throughput, current capacity, scalability, SLIs, internal SLOs, external SLAs, invariants, and error-budget policies.',
    'Design dependency-specific degradation with recovery criteria that preserves work and reduces autonomy rather than skipping controls.',
    'Enforce owner-approved retry and side-effect budgets in trusted code while leaving unsupported limits unresolved and release-blocking.',
    'Specify least privilege and privacy-safe observability with correlation IDs, versions, budgets, reason codes, and no raw broker content.',
    'Separate fixed synthetic measurement exercises from live-model, load-test, runtime, and production-readiness evidence.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/nfr_engineering.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/northstar-broker-nfrs`,
  run: 'python3 curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py',
  labs: [
    {
      title: 'Lab A — Measure and govern production qualities',
      description: 'Validate owner-sourced targets, separate semantic from compliant success, disclose small-sample latency limits, compare cost boundaries, inject governed failures, and preserve an honest blocked release.',
      command: 'python3 curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py',
      links: [['View the NFR lab', `${REPO}/blob/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/nfr_engineering.ipynb`]]
    },
    {
      title: 'Lab B — Govern AI-2219 production readiness',
      description: 'Repair a vague rollout ticket; complete workload, target, measurement, degradation, budget, and traceability artifacts; and explain every unresolved or unmeasured blocker.',
      command: 'Open the ticket and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/northstar-broker-nfrs`], ['Complete the starter package', `${REPO}/tree/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/northstar-broker-nfrs/workshop/starter`], ['Inspect the reference contract', `${REPO}/blob/main/curriculum/beginner/08-non-functional-requirements-agentic-systems/northstar-broker-nfrs/reference/nfr-contract.json`]]
    }
  ],
  references: [
    ['Google SRE — Service Level Objectives', 'https://sre.google/sre-book/service-level-objectives/'],
    ['OpenTelemetry semantic conventions', 'https://opentelemetry.io/docs/specs/semconv/'],
    ['NIST AI Risk Management Framework', 'https://www.nist.gov/itl/ai-risk-management-framework'],
    ['ISO/IEC 25010:2023 product quality model', 'https://www.iso.org/standard/78176.html']
  ],
  checkpoint: {
    question: 'The synthetic fixture passes eight NFR gates, but AI quality and six agent budgets lack owner decisions and W1 capacity has not been load-tested. What is the correct production decision?',
    options: [
      'Block production readiness, retain the bounded measurements, and obtain authorized budget, quality, and representative capacity evidence.',
      'Deploy because most synthetic gates pass.',
      'Ask the coding agent to select common quality and capacity thresholds.'
    ],
    answer: 0,
    explanation: 'A measured value cannot authorize its own target, static events do not establish capacity, and synthetic results are not production evidence. Each required characteristic retains its own state rather than disappearing into a composite score.'
  }
};

const course09 = {
  id: 'c09', course: 9, level: 'beginner', part: 'II · Executable specifications', status: 'available',
  title: 'Specification quality, review, and anti-patterns',
  summary: 'Review a plausible but unsafe enterprise specification, expose authority and evidence theater, reconcile repository reality and transition risk, and issue capability-scoped readiness before an agent implements it.',
  outcomes: [
    'Review specifications across ten quality dimensions without hiding risk inside a composite score.',
    'Detect false precision, confidence theater, implementation leakage, authority laundering, stale evidence, and unsafe exceptions.',
    'Distinguish structural trace coverage from semantic relationship validity.',
    'Detect self-confirming agent loops and resolve conflicts without treating specificity, recency, proximity, or local instructions as authority.',
    'Reconcile requirements, architecture, repository reality, migration, rollout controls, fallback, and privacy-safe observability.',
    'Bound agent permissions, budgets, stop conditions, escalation, and deployment authority.',
    'Re-review a repaired package and authorize only bounded implementation—not deployment or production release.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/09-specification-quality-review-antipatterns/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/09-specification-quality-review-antipatterns/specification_review.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/09-specification-quality-review-antipatterns/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/beginner/09-specification-quality-review-antipatterns/northstar-spec-review`,
  run: 'python3 curriculum/beginner/09-specification-quality-review-antipatterns/lab.py',
  labs: [
    {
      title: 'Lab A — Review specification quality',
      description: 'Contrast a lexical presence baseline with field-aware findings, inspect semantic trace validity, exercise false-precision and autonomy failures, and evaluate labelled review cases.',
      command: 'python3 curriculum/beginner/09-specification-quality-review-antipatterns/lab.py',
      links: [['View the lab', `${REPO}/blob/main/curriculum/beginner/09-specification-quality-review-antipatterns/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/09-specification-quality-review-antipatterns/specification_review.ipynb`]]
    },
    {
      title: 'Lab B — Review AI-2290',
      description: 'Inspect the unsafe candidate package, write reviewer-owned findings and a readiness decision, route repairs to their authoritative sources, and compare with the repaired reference.',
      command: 'Open the ticket and candidate package; complete the starter review before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/09-specification-quality-review-antipatterns/northstar-spec-review`], ['Complete the starter review', `${REPO}/tree/main/curriculum/beginner/09-specification-quality-review-antipatterns/northstar-spec-review/workshop/starter`], ['Inspect the repaired package', `${REPO}/tree/main/curriculum/beginner/09-specification-quality-review-antipatterns/northstar-spec-review/reference`]]
    }
  ],
  references: [
    ['GitHub Spec Kit — specification quality checklist', 'https://github.com/github/spec-kit/blob/main/templates/checklist-template.md'],
    ['ISO/IEC/IEEE 29148 requirements engineering', 'https://www.iso.org/standard/72089.html'],
    ['NIST AI Risk Management Framework', 'https://www.nist.gov/itl/ai-risk-management-framework'],
    ['OWASP GenAI Security Project', 'https://genai.owasp.org/']
  ],
  checkpoint: {
    question: 'Enterprise policy requires review, but a newer feature file and nearby AGENTS.md allow bypass, and repository discovery finds a direct model-facing mutation tool. Extraction remains independently bounded. What is the correct decision?',
    options: [
      'Preserve the authority conflict and trust-boundary finding, block automatic mutation, and allow only independently ready bounded capabilities.',
      'Let the newer and closer files override enterprise policy.',
      'Block every capability until the whole repository is perfect.'
    ],
    answer: 0,
    explanation: 'Specificity, recency, proximity, and repository prevalence do not transfer authority. Readiness is scoped to the affected capability, so unsafe mutation stops without destroying safe parallelism.'
  }
};

const course10 = {
  id: 'c10', course: 10, level: 'beginner', part: 'II · Executable specifications', status: 'available',
  title: 'From specification to implementation plan & agent work units',
  summary: 'Bind approved intent to repository evidence, produce complete dispositions and traceability, decompose bounded work units, and schedule safe multi-agent execution without granting implicit authority.',
  outcomes: [
    'Separate approved specifications, discovery evidence, implementation plans, agent work units, completion reports, and verification.',
    'Bind plans to exact specification, repository, architecture, instruction, and readiness-evidence revisions.',
    'Build complete requirement dispositions and bidirectional requirement-to-evidence traceability.',
    'Decompose cohesive units with exclusive write ownership, stable contracts, accountable teams, typed stop routing, and temporary permission requests.',
    'Compare contract-derived and explicit dependencies, identify the critical path, and scope unknowns to affected units.',
    'Separate implementation, verification, merge, rollout, and enablement readiness while gating verified and integrated lifecycle states.'
  ],
  readme: `${REPO}/blob/main/curriculum/beginner/10-specification-to-implementation-plan/README.md`,
  notebook: `${REPO}/blob/main/curriculum/beginner/10-specification-to-implementation-plan/implementation_planning.ipynb`,
  lab: `${REPO}/blob/main/curriculum/beginner/10-specification-to-implementation-plan/lab.py`,
  labs: [
    {
      title: 'Lab A — Validate a bounded implementation plan',
      description: 'Compare an unsafe ticket-shaped candidate with a provenance-bound plan, contract assurance, typed stops, temporary permissions, dependency waves, rollout boundaries, completion gates, and 30 labelled cases.',
      command: 'python3 curriculum/beginner/10-specification-to-implementation-plan/lab.py',
      links: [['View the lab', `${REPO}/blob/main/curriculum/beginner/10-specification-to-implementation-plan/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/beginner/10-specification-to-implementation-plan/implementation_planning.ipynb`]]
    },
    {
      title: 'Lab B — Plan AI-2219',
      description: 'Perform requirement-guided discovery, disposition every requirement, design contract-first work units, route consequential discoveries, model a mid-flight change, and separate implementation from verification and activation.',
      command: 'Open the ticket and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/beginner/10-specification-to-implementation-plan/northstar-implementation-plan`], ['Complete the starter plan', `${REPO}/tree/main/curriculum/beginner/10-specification-to-implementation-plan/northstar-implementation-plan/workshop/starter`], ['Inspect the reference package', `${REPO}/tree/main/curriculum/beginner/10-specification-to-implementation-plan/northstar-implementation-plan/reference`]]
    }
  ],
  references: [
    ['GitHub Spec Kit', 'https://github.github.com/spec-kit/'],
    ['Spec Kit plan command', 'https://github.github.com/spec-kit/reference/commands/plan.html'],
    ['OpenSpec customization', 'https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md'],
    ['Kiro specifications', 'https://kiro.dev/docs/specs/']
  ],
  checkpoint: {
    question: 'An extraction agent discovers that a shared proposal contract needs a new field. Downstream review and integration units depend on that contract. What should happen?',
    options: [
      'Pause affected work, submit a contract-change request, calculate downstream impact, obtain the owner decision, revise the plan, and re-establish readiness.',
      'Let the extraction agent edit the shared contract and ask other agents to resolve conflicts later.',
      'Mark every work unit complete because discovery is implementation progress.'
    ],
    answer: 0,
    explanation: 'A downstream discovery is a proposal, not contract authority. Impact-aware replanning preserves ownership, traceability, evidence, and safe parallelism.'
  }
};

const course11 = {
  id: 'c11', course: 11, level: 'intermediate', part: 'III · Agentic execution & SDD frameworks', status: 'available',
  title: 'Multi-Agent Coding Workflows & Coordination',
  summary: 'Design a durable coordination control plane that uses dependency waves, workload identity, leases, exclusive ownership, pull scheduling, independent evidence, bounded integration, and recovery without confusing orchestration with authority.',
  outcomes: [
    'Decide when multiple agents provide enough flow benefit to justify coordination cost.',
    'Separate orchestration, execution, verification, integration, and accountable decision rights.',
    'Derive safe execution waves from dependencies, stable contracts, pinned context, and exclusive write ownership.',
    'Use authenticated workload identities, temporary permissions, assignment leases, logical locks, and bounded delegation.',
    'Design typed handoffs, events, idempotency, retries, recovery, evidence invalidation, and contract-change propagation.',
    'Optimize total delivery flow using work-in-progress limits and implementation plus human-review capacity.',
    'Evaluate coordination, integration, rework, review load, and forbidden attempts without claiming a general productivity benchmark.'
  ],
  readme: `${REPO}/blob/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/README.md`,
  notebook: `${REPO}/blob/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/multi_agent_coordination.ipynb`,
  lab: `${REPO}/blob/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/northstar-multi-agent-delivery`,
  run: 'python3 curriculum/intermediate/01-multi-agent-coding-workflows-coordination/lab.py',
  labs: [
    {
      title: 'Lab A — Validate the coordination control plane',
      description: 'Compare unsafe parallel execution with a governed workflow, exercise just-in-time dispatch, idempotency, lease/identity lifetimes, delegation, typed transition evidence, integration, recovery, and 36 labelled cases.',
      command: 'python3 curriculum/intermediate/01-multi-agent-coding-workflows-coordination/lab.py',
      links: [['View the lab', `${REPO}/blob/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/multi_agent_coordination.ipynb`]]
    },
    {
      title: 'Lab B — Coordinate Northstar AI-2219',
      description: 'Complete the workflow, handoff, and recovery artifacts for a six-unit delivery graph before comparing with the reference control-plane package.',
      command: 'Open the scenario and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/northstar-multi-agent-delivery`], ['Complete the starter artifacts', `${REPO}/tree/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/northstar-multi-agent-delivery/workshop/starter`], ['Inspect the reference package', `${REPO}/tree/main/curriculum/intermediate/01-multi-agent-coding-workflows-coordination/northstar-multi-agent-delivery/reference`]]
    }
  ],
  references: [
    ['Git worktree documentation', 'https://git-scm.com/docs/git-worktree'],
    ['GitHub rulesets', 'https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets'],
    ['OpenTelemetry CI/CD conventions', 'https://opentelemetry.io/docs/specs/semconv/cicd/'],
    ['SPIFFE workload identity', 'https://spiffe.io/docs/latest/spiffe/concepts/'],
    ['NIST Zero Trust Architecture', 'https://csrc.nist.gov/pubs/sp/800/207/final']
  ],
  checkpoint: {
    question: 'Two wave-two units are ready, but the domain-review queue is at capacity. What should the scheduler do?',
    options: [
      'Pull only the unit whose review capacity is available; leave the other unassigned until dispatch can bind short-lived resources.',
      'Start both to maximize agent utilization and defer review.',
      'Remove the domain-review requirement because the dependency graph is acyclic.'
    ],
    answer: 0,
    explanation: 'Review capacity is part of system capacity. Pull scheduling keeps waiting work unassigned and binds identity, permission, lease, and lock only when dispatch can proceed.'
  }
};

const course12 = {
  id: 'c12', course: 12, level: 'intermediate', part: 'III · Agentic execution & SDD frameworks', status: 'available',
  title: 'SDD Framework Landscape & Choosing an Enterprise Operating Model',
  summary: 'Compare framework semantics, preserve organization-owned authority, map portable artifacts, choose proportional operating modes, and test adapters and upgrades without declaring a universal tool winner.',
  outcomes: [
    'Distinguish methodology, framework, repository instructions, and enterprise operating model.',
    'Compare Spec Kit, OpenSpec, Kiro Specs, BMad, and repo-native approaches from dated official sources.',
    'Profile capabilities as built into a synthetic style, supplied by enterprise extensions, enforced externally, or not modeled—without hiding mandatory gaps in an overall score.',
    'Map framework artifacts to a canonical model with business, policy, architecture, execution, evidence, and release authority.',
    'Validate specification, plan, task, and implementation transformations before generated output flows downstream.',
    'Route changes through proportional risk tiers and preserve a lightweight path for low-risk work.',
    'Write a reviewable framework-selection ADR and protect upgrades with migration tests and golden scenarios.'
  ],
  readme: `${REPO}/blob/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/README.md`,
  notebook: `${REPO}/blob/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/framework_landscape.ipynb`,
  lab: `${REPO}/blob/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/lab.py`,
  repoFixture: `${REPO}/tree/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/northstar-framework-selection`,
  run: 'python3 curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/lab.py',
  labs: [
    {
      title: 'Lab A — Validate the operating model',
      description: 'Contrast an unsafe feature contest with four enterprise-enriched workflow styles, inspect capability profiles, route risk tiers, run migration checks, and exercise 34 labelled failures.',
      command: 'python3 curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/lab.py',
      links: [['View the selection lab', `${REPO}/blob/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/lab.py`], ['Use the guided notebook', `${REPO}/blob/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/framework_landscape.ipynb`]]
    },
    {
      title: 'Lab B — Select the Northstar SDD composition',
      description: 'Evaluate AI-2310 against identical source context, complete the capability and selection artifacts, preserve unresolved authority, and compare with the review-ready reference.',
      command: 'Open the source package and starter workspace; run Lab A before consulting the reference.',
      links: [['Open the workshop', `${REPO}/tree/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/northstar-framework-selection`], ['Complete the starter decision', `${REPO}/tree/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/northstar-framework-selection/workshop/starter`], ['Inspect the reference model', `${REPO}/tree/main/curriculum/intermediate/02-sdd-framework-landscape-enterprise-operating-model/northstar-framework-selection/reference`]]
    }
  ],
  references: [
    ['GitHub Spec Kit', 'https://github.github.com/spec-kit/'],
    ['OpenSpec overview', 'https://github.com/Fission-AI/OpenSpec/blob/main/docs/overview.md'],
    ['Kiro Specs', 'https://kiro.dev/docs/specs/'],
    ['BMad Method', 'https://docs.bmad-method.org/'],
    ['AGENTS.md open format', 'https://github.com/agentsmd/agents.md']
  ],
  checkpoint: {
    question: 'A spec-first framework produces excellent plans and tasks but has no enterprise policy resolver, authenticated approvals, or evidence service. What is the sound adoption decision?',
    options: [
      'Use it for the bounded project workflow if clean adapters and external controls satisfy those mandatory capabilities; do not call the framework governance.',
      'Reject it automatically because every capability must be built into the workflow style.',
      'Treat generated plans as approved because the workflow is structured.'
    ],
    answer: 0,
    explanation: 'Enterprise fit is compositional. A framework can implement the project transformation workflow while the accountable team and organization-owned services retain policy, authority, evidence, execution, and release decisions.'
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
  course07,
  course08,
  course09,
  course10,
  course11,
  course12,
  planned(13, 'intermediate', 'III · Agentic execution & SDD frameworks', 'GitHub Spec Kit', 'Run one Northstar change through the full Spec Kit lifecycle under the enterprise authority boundary.'),
  planned(14, 'intermediate', 'III · Agentic execution & SDD frameworks', 'OpenSpec', 'Manage current specifications and explicit change deltas for brownfield work.'),
  planned(15, 'intermediate', 'III · Agentic execution & SDD frameworks', 'Kiro Specs', 'Apply feature, bug-fix, and quick-spec workflows with appropriate approval depth.'),
  planned(16, 'intermediate', 'III · Agentic execution & SDD frameworks', 'Agent instructions & custom enterprise adapters', 'Combine scoped cross-agent guidance with versioned context, evidence, conformance, and upgrade adapters.'),
  planned(17, 'intermediate', 'IV · Agentic PDLC', 'Idea → discovery → spec → design → implementation', 'Build an end-to-end flow with explicit state, owners, gates, and handoffs.'),
  planned(18, 'intermediate', 'IV · Agentic PDLC', 'Brownfield development', 'Recover system truth before changing code with incomplete or stale specifications.'),
  planned(19, 'intermediate', 'IV · Agentic PDLC', 'Bug fixes and small changes', 'Use a proportional workflow that preserves evidence without process theatre.'),
  planned(20, 'intermediate', 'IV · Agentic PDLC', 'Multi-repository development', 'Coordinate contracts, versions, sequencing, and ownership across repositories.'),
  planned(21, 'intermediate', 'IV · Agentic PDLC', 'Multi-repository parallel-agent delivery', 'Extend bounded coordination across repository, contract, release, and integration boundaries.'),
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
