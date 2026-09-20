# Impact analysis — AI-030 v3 to v4

The v4 candidate adds a changed fixed obligation. `ARCH-031` is a direct specialization and must be re-evaluated against it. `REQ-REN-004`, `ReviewServiceAdapter`, and `TEST-REVIEW-004` are downstream consumers reached through the relationship graph; additional graph descendants may also be review candidates.

AI Governance owns the changed meaning. Project Architecture re-evaluates `ARCH-031`. Renewal Product rechecks feature acceptance. Underwriter Engineering and the Review Platform reassess implementation and runtime enforcement. AI Quality and test owners regenerate evidence where the changed control affects their claims.

“Affected” means the old assurance is insufficient for the new revision. It does not, by itself, prove compliance or non-compliance. The agent stops until accountable owners review the changed obligation, update bindings, and regenerate required evidence.
