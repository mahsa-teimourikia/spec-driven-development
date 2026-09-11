# Enterprise Spec-Driven Development

> A 38-course learning program for designing an enterprise operating model in which coding agents can move quickly without receiving unlimited freedom.

## Start here

Open the **[deployed Learning Hub](https://mahsa-teimourikia.github.io/spec-driven-development/hub/)** and begin with [Course 01: Why agentic coding changes the PDLC](curriculum/beginner/01-why-agentic-coding-changes-pdlc/README.md). The course includes a guided [notebook](curriculum/beginner/01-why-agentic-coding-changes-pdlc/agentic_pdlc.ipynb), [Lab A's deterministic control-plane model](curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py), [Lab B's realistic repository change](curriculum/beginner/01-why-agentic-coding-changes-pdlc/northstar-underwriter/README.md), and a [deployed knowledge check](https://mahsa-teimourikia.github.io/spec-driven-development/quiz/).

This is not simply a tutorial for one specification framework. The central skill is turning organizational intent, architecture rules, product requirements, and engineering constraints into a hierarchy of durable specifications that agents can execute—and humans can govern.

## The learning journey

| Part | Courses | Focus |
| --- | ---: | --- |
| I · SDD foundations | 01–04 | Why the PDLC changes and how specifications form a hierarchy |
| II · Executable specifications | 05–10 | Requirements, scenarios, invariants, NFRs, ADRs, and traceability |
| III · SDD frameworks | 11–16 | Spec Kit, OpenSpec, Kiro, agent instructions, selection, and extensions |
| IV · Agentic PDLC | 17–23 | Delivery flows, brownfield work, parallel agents, reviews, and approvals |
| V · Enterprise controls | 24–31 | Security, AI governance, architecture, quality, compliance, and CI/CD |
| VI · Advanced agentic SDD | 32–38 | Context engineering, orchestration, drift, continuous specs, and evaluation |

The program ends with an **Enterprise Agent capstone**: design a real Agentic PDLC with authority boundaries, policy enforcement, evidence, exception handling, and measurable outcomes. See the [complete course plan](COURSE_PLAN.md).

## Course 01 outcome

Course 01 uses a fictional financial-services organization, Northstar Mutual, to show how the PDLC becomes a governed control loop. You will:

- distinguish prompts from durable specifications and observable evidence;
- discover distributed context and resolve requirement applicability before precedence;
- compose organization, platform, domain, project, feature, and implementation rules with provenance;
- detect policy conflicts rather than silently allowing lower-level overrides;
- run unsafe and governed candidate code in a temporary repository and compare independent gates;
- generate a traceable release evidence bundle while naming what it cannot prove;
- choose direct change, lightweight specification, or full SDD in proportion to risk; and
- interpret current evidence about agentic coding without confusing speed with safe delivery.

## Run locally

Everything in Course 01 is credential-free and uses the Python standard library.

```bash
python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py
python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/repo_lab.py --candidate all
python3 -m unittest discover -s tests -v
python3 scripts/validate_course.py
```

To preview the Hub:

```bash
python3 -m http.server 8000
```

Then visit <http://localhost:8000/hub/>. Jupyter is optional; the repository validator executes the notebook top to bottom without requiring a notebook server.

## Operating principles

1. **Intent is hierarchical.** A feature specification inherits organization, platform, domain, and project constraints.
2. **Autonomy is bounded.** Agents receive explicit permissions, budgets, stop conditions, and escalation paths.
3. **Evidence closes the loop.** Tests, policy results, reviews, and production signals determine whether intent was satisfied.
4. **Controls are executable where practical.** Prose explains policy; schemas, tests, and CI gates enforce it.
5. **Ceremony is proportional.** Small, reversible changes do not need the same process as regulated, cross-repository work.
6. **Specifications evolve.** Drift must be detected and reconciled rather than hidden.

## Frameworks in the course

The program progressively uses [GitHub Spec Kit](https://github.github.com/spec-kit/), [OpenSpec](https://github.com/Fission-AI/OpenSpec), [Kiro Specs](https://kiro.dev/docs/specs/), `AGENTS.md`-style instructions, ADRs, policy-as-code, CI gates, evaluation, and multi-agent workflows. Frameworks are treated as implementation choices inside a broader operating model.

Learning with One+i · responsible AI, real-world impact. [oneplusi.io](https://oneplusi.io)
