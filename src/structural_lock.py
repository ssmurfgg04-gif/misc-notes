"""structural_lock.py — E4: exploit f = 1 - sumB/sumM (plan.md A17).

Inference-time recipe (per window):
  1. Site s = site_id.assign(window)                         (E3)
  2. Predict background total sumB_hat from site-conditional
     background model (fit on train background windows only — no test fitting, A22).
  3. f_lock = clip(1 - sumB_hat/sumM, 0, 1)
  4. Fuse: f_hat = w * f_model + (1-w) * f_lock  (w fixed on validation, never LB).

Ablation table (E4 acceptance): RMSE of
  (a) model only, (b) lock only, (c) fused, each with/without site-conditional sumB.
Self-test on synthetic data where sites have distinct background levels.
"""
import numpy as np


class LockModel:
    """Site-conditional background-total predictor (median of train background sums)."""

    def __init__(self, site_centroids=None):
        self.site_centroids = site_centroids or {}

    def fit(self, sumB, sites):
        self.site_centroids = {}
        for s in sorted(set(sites)):
            self.site_centroids[s] = float(np.median(sumB[np.array(sites) == s]))
        self.global_median = float(np.median(sumB))
        return self

    def predict_sumB(self, sites):
        return np.array([self.site_centroids.get(s, self.global_median) for s in sites])


def lock_f(W, sumB_hat):
    """W: (n,15,25) linear mixed windows -> f_lock = 1 - sumB_hat/sumM."""
    sumM = np.nanmean(W.astype(np.float64), axis=(1, 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        f = 1.0 - np.asarray(sumB_hat) / sumM
    return np.clip(f, 0.0, 1.0)


def ablation_table(W, f_true, f_model, sites_bg_model, sites_true_for_lock=None,
                   use_site_conditioning=True):
    """Returns RMSE ablation dict. f_model: two-head regression predictions."""
    sumM = np.nanmean(W.astype(np.float64), axis=(1, 2))
    out = {}
    out["model_only"] = float(np.sqrt(np.mean((f_model - f_true) ** 2)))
    if use_site_conditioning:
        sumB_hat = sites_bg_model.predict_sumB(sites_true_for_lock)
    else:
        sumB_hat = np.full(len(f_true), sites_bg_model.global_median)
    f_lock = lock_f(W, sumB_hat)
    out["lock_only"] = float(np.sqrt(np.mean((f_lock - f_true) ** 2)))
    for w in (0.3, 0.5, 0.7):
        f_fuse = w * f_model + (1 - w) * f_lock
        out[f"fused_w{w}"] = float(np.sqrt(np.mean((f_fuse - f_true) ** 2)))
    # oracle sumB (upper bound of lock): uses true background totals if provided
    return out, f_lock


def selftest(seed=5):
    """Synthetic: 4 sites, 30 dB level spread; lock should beat zero-const clearly."""
    rng = np.random.default_rng(seed)
    n_per, n_sites = 300, 4
    B_tot_db = np.repeat(rng.uniform(70, 100, n_sites), n_per)
    B_shape = rng.uniform(-3, 3, (n_per * n_sites, 25))
    f = rng.choice([0.0, 0.1, 0.2, 0.3, 0.4], size=n_per * n_sites)
    # vessel shape roughly flat, small relative to background per band
    V_shape = rng.uniform(0.5, 1.5, (n_per * n_sites, 25)) * 1e-3
    B_lin = (10 ** (B_tot_db / 10.0))[:, None] * (10 ** (B_shape / 10.0))
    B_lin /= B_lin.sum(axis=1, keepdims=True) / (10 ** (B_tot_db / 10.0))[:, None]
    V_lin = V_shape * (10 ** (B_tot_db / 10.0))[:, None] * 1e-6
    sumB = B_lin.sum(1)
    sumV = V_lin.sum(1)
    alpha = np.where(f > 0, (f / np.maximum(1 - f, 1e-9)) * sumB / sumV, 0.0)
    W = B_lin[:, None, :] + alpha[:, None, None] * V_lin[:, None, :]
    # 'model' = noisy estimate of f
    f_model = f + rng.normal(0, 0.08, len(f))
    f_model = np.clip(f_model, 0, 1)
    # site labels assumed known (E3 output); fit lock on train half
    sites = np.repeat([f"s{i}" for i in range(n_sites)], n_per)
    tr = np.arange(len(f)) % 2 == 0
    lm = LockModel().fit(sumB[tr], sites[tr])
    tab, f_lock = ablation_table(W[~tr], f[~tr], f_model[~tr], lm, sites[~tr])
    zero = float(np.sqrt(np.mean(f[~tr] ** 2)))
    tab["zero_const"] = zero
    return tab


if __name__ == "__main__":
    import json
    print(json.dumps(selftest(), indent=2))
