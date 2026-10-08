# ADR-058@3-training — Document extraction architecture

The existing OCR pipeline owns PDF extraction. `SubmissionService` owns authoritative underwriting requirement state. The document agent may create non-authoritative proposals but has no mutation tool for satisfying requirements.

Changing extraction architecture, authorization semantics, or authoritative submission mutation requires a separate proposal and accountable review.
