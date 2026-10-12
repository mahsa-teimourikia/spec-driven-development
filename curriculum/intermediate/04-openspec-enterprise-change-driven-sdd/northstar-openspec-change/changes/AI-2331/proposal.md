# Proposal — AI-2331 automated document triage

## Why

Operations wants to route documents to queues more quickly.

## What changes

- use a triage decision to select a downstream queue; and
- modify the current document-classification behavior.

## Capabilities

### Modified capabilities

- `document-processing`

## Impact

The proposal modifies `REQ-DOC-014@3`, which is also modified by active change `AI-2310`. It is blocked pending conflict disposition and rebase.

