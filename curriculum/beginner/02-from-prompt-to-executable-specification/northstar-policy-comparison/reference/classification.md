# Reference classification for AI-1842

| Statement | Destination | Disposition | Why |
|---|---|---|---|
| Add policy comparison | Product intent | Keep | States the outcome, not the conformance boundary. |
| Select two policies and compare coverage | Candidate requirement | Clarify then specify | Observable behavior, but authorization, document count, actors, and failure behavior were missing. |
| Use existing RAG | Design hypothesis | Validate | It is a solution choice. The product owner did not establish it as an architecture constraint. |
| Accurate and explain differences | Open question | Replace | “Accurate” has no measure. It becomes citation completeness, citation correctness, claim faithfulness, and abstention-correctness requirements. |
| Cache comparisons | Design hypothesis | Evaluate | Cost is a concern; caching is one possible response with privacy, freshness, and authorization consequences. |
| Sarah mentioned human approval | Policy lead | Verify | Hearsay is not policy. AI-021 supplies the authoritative rule and owner. |
| Latency under 3 seconds | Performance aspiration | Replace | It lacks percentile, workload, scope, and measurement point. SLO-CMP-001 provides them. |
| Use Redis | Rejected design prescription | Do not inherit | Another team's use is not an architecture decision. Compare alternatives in an ADR if caching is pursued. |

The classification uses source and decision rights, not grammar alone. If an authorized architecture standard required the existing RAG gateway, the same words could represent a constraint rather than a suggestion.

The course function `teaching_classify_statement()` is an intentionally limited teaching heuristic. It helps learners inspect provenance, authority, and destination; it must not assign authority, approve artifacts, or update enterprise records automatically.
