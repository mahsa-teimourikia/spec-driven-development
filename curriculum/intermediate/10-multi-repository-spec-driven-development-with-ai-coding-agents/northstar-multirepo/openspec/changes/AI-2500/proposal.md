# AI-2500 — Broker Document Review

## Why

Northstar needs an AI-assisted document-classification proposal that preserves provenance, routes ambiguity to authorized review, and never mutates authoritative underwriting state by itself.

## What changes

- revise `CONTRACT-CLASSIFICATION-001` from revision 1 to revision 2;
- add evidence and model provenance to every proposal;
- make Review Service v2 tolerant of revisions 1 and 2;
- deploy the tolerant consumer before the new producer; and
- verify an exact five-repository revision set before integration review.

## Authority boundary

This proposal does not approve the contract, architecture, merge, deployment, activation, or retirement of revision 1.
