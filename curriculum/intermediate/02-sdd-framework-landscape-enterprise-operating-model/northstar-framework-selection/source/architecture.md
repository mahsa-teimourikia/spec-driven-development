# Existing architecture

The brownfield service already exposes `DocumentEnvelope@4`, routes model calls through the approved AI gateway, and stores review proposals separately from underwriting decisions. `ADR-058@3` prohibits document text from changing tool permissions. The classification change may reuse these boundaries; changing them requires an architecture proposal and owner review.

