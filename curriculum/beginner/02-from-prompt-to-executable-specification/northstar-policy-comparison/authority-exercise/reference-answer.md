# Reference answer — same technology, different meaning

No: these are not the same requirement.

| Statement | Artifact | Authority | Durable? | Agent action | Why? |
|---|---|---|---|---|---|
| Jira: “Use Bedrock.” | Design suggestion embedded in feature input | Product input, not architecture authority | No | Clarify the underlying outcome; evaluate rather than inherit | The ticket has no governing source, approved scope, rationale, or exception route. |
| Slack: “We normally use Bedrock.” | Informal context or architecture lead | Informal engineering precedent | No | Verify against an ADR, standard, or platform policy | A role name and chat location do not create decision authority. |
| PLAT-007 policy | Inherited platform constraint | AI Platform Architecture | Yes, while applicable and current | Inherit the approved gateway boundary; verify applicability and revision | The record names its owner, scope, revision, rule, and exception mechanism. |

The policy requires the approved **gateway**, not merely the provider name. The implementation agent may not infer permission to call a direct Bedrock endpoint.

```text
same technology
≠ same artifact
≠ same authority
≠ same lifecycle
≠ same agent action
```

The meaning of an enterprise instruction comes from its words **and** its provenance, ownership, scope, authority, lifecycle, applicability, freshness, and exception mechanism.
