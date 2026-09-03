# Recoup Batch Recovery Benchmark

This benchmark is designed for the Razorpay AI Buildathon Revenue Recovery track.
Razorpay's current bar is to show **measured money recovered across a batch**, with compliant escalation, stopping rules, and an audit trail.

The benchmark generates a deterministic synthetic batch and runs the same Gemini triage + strategy prompts used by Recoup. It then compares the resulting decision against synthetic ground truth and a deterministic customer-response simulator.

## Run

```bash
python -m evaluation.batch_recovery_eval --n 100
python -m evaluation.batch_recovery_eval --n 500 --concurrency 8
```

Requires `GEMINI_API_KEY` in the environment.

## Important honesty rule

The `simulated_amount_recovered_inr` metric is **not real money recovered**. It is a synthetic benchmark outcome. It should be presented to judges as a controlled evaluation unless the system is later connected to a genuine test-mode cohort where payment outcomes can be observed.

The benchmark is useful for demonstrating:

- decision accuracy across a batch
- escalation behavior
- error rate
- amount-at-risk coverage
- simulated recovery amount/rate
- per-scenario performance

The final Buildathon submission should pair these results with Recoup's real execution/audit trail and, where possible, actual test-mode payment-link outcomes.
