# AI-2176 workshop — Broker Follow-up Assistant

The product ticket sounds clear until a coding agent must decide what counts as missing, which source
is authoritative, who may approve a message, and whether “simple” cases may be sent automatically.
Your goal is to convert that ambiguity into a bounded requirements package without inventing policy.

## Your assignment

1. Read [`ticket/AI-2176.md`](ticket/AI-2176.md).
2. Inspect the versioned [underwriting rules](sources/underwriting-requirements.json),
   [stakeholder decisions](sources/stakeholder-decisions.md), and
   [operating baseline](sources/operating-baseline.json).
3. Complete the [starter requirements package](workshop/starter/requirements-package.json) and
   [ambiguity register](workshop/starter/ambiguity-register.md).
4. Run the deterministic quality and runtime-boundary lab:

   ```bash
   python3 curriculum/beginner/05-requirements-engineering-for-agents/lab.py \
     --package curriculum/beginner/05-requirements-engineering-for-agents/northstar-broker-follow-up/workshop/starter/requirements-package.json
   ```

5. Compare your decisions with the [reference package](reference/requirements-package.json) only
   after you can explain every open question, stop condition, and requirement-to-task link.

## Expected result

Missing-item analysis and drafting can progress as bounded, review-only capabilities. Automatic send
remains disabled because `OQ-017` is unresolved. This is intentional: one open question blocks only
the capability whose safety and authority depend on it.

## Evidence boundary

The fixture proves deterministic behavior over synthetic inputs. It does not authenticate owners,
evaluate a language model, contact a broker, prove delivery, or define production quality thresholds.
