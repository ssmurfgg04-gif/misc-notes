"""site_id.py — E3: window -> station assignment from (level, tilt, band-share, nan pattern).

Method: nearest-centroid in standardized log-space + margin-based confidence.
Fit on BACKGROUND-only windows per site (station centroids); assign test windows by
nearest centroid; "confident" = margin between top-1 and top-2 centroid distances
exceeds tau. Report confusion matrix on held-out background windows (E3 acceptance:
>=90% confident assignment; confusion matrix reported).

This module is TEST-DATA-FREE until inference; fit uses only background data
(rules: site-ID is an unsupervised/background-level transform, A22-compliant).
"""
import json
import numpy as np


def window_descriptor(W):
    """W: (n,15,25) linear -> (n, D) descriptor: [total dB, tilt, band-share(25), nan-rate, min-std]."""
    lin = W.astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10.0 * np.log10(lin)
    total = np.nanmean(lin, axis=(1, 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        total_db = 10.0 * np.log10(total)
    band_db = np.nanmean(db, axis=1)
    lf = np.log10(10.0 ** (1.5 + 0.1 * np.arange(25)))
    A = np.stack([np.ones_like(lf), lf], axis=1)
    coef, *_ = np.linalg.lstsq(A, band_db.T, rcond=None)
    tilt = coef[1]
    share = np.nanmean(lin, axis=1) / total[:, None]
    nan_rate = np.isnan(lin).mean(axis=(1, 2))
    min_db = 10.0 * np.log10(np.nanmean(lin, axis=2))
    min_std = np.nanstd(min_db, axis=1)
    return np.stack([total_db, tilt, nan_rate, min_std] + [share[:, k] for k in range(25)], axis=1)


class SiteID:
    def __init__(self, tau=1.0):
        self.tau = tau
        self.centroids = None
        self.mu = None
        self.sd = None

    def fit(self, desc, site_keys):
        self.mu = np.nanmean(desc, axis=0)
        self.sd = np.nanstd(desc, axis=0) + 1e-9
        Z = (desc - self.mu) / self.sd
        self.sites = sorted(set(site_keys))
        self.centroids = {s: np.nanmean(Z[np.array(site_keys) == s], axis=0) for s in self.sites}
        return self

    def assign(self, desc):
        Z = (desc - self.mu) / self.sd
        S = np.array([self.centroids[s] for s in self.sites])         # (K,D)
        d = np.linalg.norm(Z[:, None, :] - S[None, :, :], axis=2)     # (n,K)
        top = np.argsort(d, axis=1)
        best, second = top[:, 0], top[:, 1]
        margin = d[np.arange(len(d)), second] - d[np.arange(len(d)), best]
        site = np.array(self.sites)[best]
        confident = margin > self.tau
        return site, confident, margin, d

    def confusion(self, desc, true_sites):
        pred, conf, margin, _ = self.assign(desc)
        K = len(self.sites)
        C = np.zeros((K, K), dtype=int)
        for t, p in zip(true_sites, pred):
            C[self.sites.index(t), self.sites.index(p)] += 1
        acc = float((pred == np.array(true_sites)).mean())
        acc_conf = float((pred[conf] == np.array(true_sites)[conf]).mean()) if conf.any() else float("nan")
        return {"matrix": C.tolist(), "sites": self.sites, "accuracy": acc,
                "accuracy_on_confident": acc_conf, "confident_rate": float(conf.mean())}


def selftest(n_sites=10, seed=3):
    """Synthetic sanity check: separable site distributions -> accuracy & confusion."""
    rng = np.random.default_rng(seed)
    n = 120
    descs, keys = [], []
    for s in range(n_sites):
        base = rng.normal(0, 1, desc_dim()) + rng.normal(0, 0.4, desc_dim())
        descs.append(base[None, :] + rng.normal(0, 0.25, (n, desc_dim())))
        keys += [f"site{s}"] * n
    D = np.vstack(descs)
    K = np.array(keys)
    tr = rng.random(len(K)) < 0.7
    model = SiteID(tau=0.5).fit(D[tr], K[tr])
    return model.confusion(D[~tr], K[~tr])


def desc_dim():
    return 4 + 25


if __name__ == "__main__":
    r = selftest()
    print(json.dumps(r, indent=2))
