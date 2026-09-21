# AI-2219 scenario set

The structured scenarios are in [`scenarios.json`](scenarios.json). This human-readable set samples
the important behavioral boundaries; it is not claimed to exhaust the state space.

## AC-BR-005-A — verified conflict

```gherkin
Given submission SUB-42 has verified construction_year 1998
And broker BROKER-19 is authorized for SUB-42
When authenticated response MSG-882 proposes construction_year 2001
Then the ProposedUpdate status is CONFLICTING
And construction_year remains 1998
And MSG-882 and its source span remain linked as evidence
```

`REQ-BR-005` owns the `CONFLICTING` classification. `REQ-BR-001` and `INV-BR-002` independently
prohibit automatic replacement. The scenario demonstrates both without merging their authority.

## AC-BR-CONFLICT-REVIEW-01 — explicit replacement resolution

```gherkin
Given a CONFLICTING ProposedUpdate entered AWAITING_REVIEW
And an authorized reviewer selected replace_verified_value
And the unused, unexpired receipt binds the exact proposal digest, submission revision, and requirement-context digest
When authoritative application is requested
Then the proposal may transition through APPROVED to APPLIED
And no different proposal or resolution inherits the approval
```

## AC-BR-AUTH-01 — unauthorized response

```gherkin
Given the response principal is not authorized for SUB-42
When the response proposes a supported value
Then processing is blocked before content evaluation
And submission state remains unchanged
```

## AC-BR-STALE-01 — stale proposal

```gherkin
Given a proposal was created against submission revision S17
And the current submission revision is S18
When application is requested
Then the proposal becomes STALE
And submission state remains unchanged
```

## AC-BR-DUP-01 — duplicate response

```gherkin
Given response MSG-882 already produced an authoritative mutation
When MSG-882 is delivered again
Then no second mutation occurs
And the duplicate reason is recorded
```
