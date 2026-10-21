# Validation protocol (E5) — written before looking at any public-LB feedback

## Principle
All model selection happens on synthetic holdouts with grouped splits and on
structural ablations. The public LB (30% of test) is a **smoke test only** —
never a tuning signal (A20/A22; 2/day budget). Private = 70%; select 2
diversified submissions (A23).

## Splits (window level, synthetic)
| split | held out | purpose |
|---|---|---|
| clip-held-out | 20% of VTUAD vessel clips | reference-identity generalization |
| site-held-out | 20% of SA sites | site generalization (recorder/condition shift) |
| both-held-out | union | worst case; submission model uses this protocol's report |

Site-ID centroids, lock medians, and all statistics are fit on **train slices
only** (A22: fit on train, assign on test).

## Baselines reported alongside every result
- zero-const: RMSE = RMS(f_val) — equals the benchmark predictor under the
  anchor (A15: RMS(f)=0.2461 on test-like marginals).
- mean-const: train-optimal constant (≈ std(f) = 0.141 for the uniform grid).

## Acceptance gates used in R4
1. synth f-marginal: RMS 0.24±0.03, E[f²]=0.060±0.006 (anchor-faithful, A16 restated).
2. model beats zero-const AND mean-const on all three splits.
3. A17 ablation: removing total-energy features must not collapse RMSE
   (confirms shape-carries-signal; guards against energy-leak artifacts).
4. site-ID: ≥90% accuracy on confident assignments; confusion matrix reported;
   coverage reported honestly (26–33% at τ=1.0).

## Synthetic–real gap (declared)
All RMSEs above are **synthetic-domain** numbers: val windows share the generator's
signatures (same SA background distribution, same transform family). They are an
optimistic ceiling, not an LB forecast (R2 caveat, unchanged). The residual
synthetic–real gap will be quantified as `LB_score − local_score` at the first
smoke-test submission and recorded here; scenario re-weighting is the designated
response if the gap is large (plan.md §4 R5 guard).

## Submission discipline
- Smoke test: 1 submission of the primary two-head (recipe-based).
- Private pair (diversified, A23/E6): (a) recipe-based two-head on primary grid;
  (b) hedge ensemble (weighted-low + nonuniform + primary) or shape-only variant —
  chosen by held-out RMSE, never by public LB rank.
- Raw [0,1] floats, no rounding (rules).

## R4 results recorded under this protocol
See plan.md §6e table (clip/site/both: 0.0522/0.0434/0.0493; AUC 0.997–0.998;
ablations and negative lock result). Artifact: `data/train_v2/train_report_v2.json`.
