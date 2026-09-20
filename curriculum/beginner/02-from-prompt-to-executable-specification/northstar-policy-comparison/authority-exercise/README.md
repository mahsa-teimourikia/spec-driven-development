# Authority exercise — same technology, different meaning

Read the three sources before opening the reference answer:

1. [`01-jira.md`](01-jira.md)
2. [`02-architecture-slack-note.md`](02-architecture-slack-note.md)
3. [`03-platform-policy.md`](03-platform-policy.md)

They all mention Bedrock. Are they the same requirement?

Complete this table using source, owner, scope, authority, lifecycle, durability, and exception mechanism—not technology keywords alone.

| Statement | Artifact | Authority | Durable? | Agent action | Why? |
|---|---|---|---|---|---|
| Jira: “Use Bedrock.” | TODO | TODO | TODO | TODO | TODO |
| Slack: “We normally use Bedrock.” | TODO | TODO | TODO | TODO | TODO |
| Policy: “Production inference SHALL use the approved enterprise Bedrock gateway.” | TODO | TODO | TODO | TODO | TODO |

Then answer:

1. What underlying outcome might the Jira author actually need?
2. What would make the Slack note durable and authoritative?
3. Which source defines the production boundary and exception path?
4. May the implementation agent infer that direct Bedrock API access is approved?

Only after committing to your answers, compare them with [`reference-answer.md`](reference-answer.md).
