#!/usr/bin/env python3
"""TOL converter: audio -> minute-level 25-band mean-square values.

Replicates the documented organiser conversion (maritime_starter_notebook,
cell 11): non-overlapping 2 s segments, per-segment mean removal, one-sided
Hann periodogram (density scaling), integration over base-10 third-octave
bands centred at 10^(1.5+0.1k), linear mean of 30 segments per minute,
NaN for unsupported bands, trailing partial minute dropped.
"""
import numpy as np

CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))   # 31.6228 Hz .. 7943.28 Hz
BAND_LO = CENTRES / 10 ** 0.05
BAND_HI = CENTRES * 10 ** 0.05


def minute_band_power(samples, sample_rate_hz):
    """One-channel audio -> (minutes, 25) mean-square band values."""
    from scipy.signal import periodogram
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim != 1 or not np.isfinite(samples).all():
        raise ValueError("Use one channel with finite samples.")
    fs = float(sample_rate_hz)
    if not np.isfinite(fs) or fs <= 0 or not fs.is_integer():
        raise ValueError("Use the actual integer sample rate.")
    segment_size = int(2 * fs)
    minutes = samples.size // (30 * segment_size)
    if minutes == 0:
        raise ValueError("At least one complete minute needed.")
    segments = samples[:minutes * 30 * segment_size].reshape(-1, segment_size)
    frequency, psd = periodogram(segments, fs=fs, window="hann", detrend="constant",
                                 return_onesided=True, scaling="density", axis=1)
    power = np.full((len(segments), 25), np.nan)
    df = frequency[1] - frequency[0]
    for band in range(25):
        bins = (frequency >= BAND_LO[band]) & (frequency < BAND_HI[band])
        if BAND_HI[band] <= fs / 2 and bins.any():
            power[:, band] = psd[:, bins].sum(axis=1) * df
    return power.reshape(minutes, 30, 25).mean(axis=1)


def tol_db(power):
    """linear band power -> dB (floor at tiny value to avoid -inf)."""
    return 10.0 * np.log10(np.maximum(power, 1e-30))


if __name__ == "__main__":
    # self-test: white noise + 1 kHz tone, verify band energies land plausibly
    rng = np.random.default_rng(0)
    fs = 32000
    t = np.arange(3 * 60 * fs) / fs
    x = rng.normal(0, 1, t.size) + 3.0 * np.sin(2 * np.pi * 1000 * t)
    p = minute_band_power(x, fs)
    db = tol_db(p)
    k1000 = int(np.argmin(np.abs(CENTRES - 1000)))
    assert p.shape == (3, 25)  # 3 minutes of audio -> 3 minute-rows
    assert np.isfinite(p).all(), "32 kHz supports all 25 bands"
    assert db[:, k1000].mean() > db[:, k1000 - 3].mean() + 5, "tone band must dominate"
    print("TOL converter self-test OK. tone band dB:", round(float(db[:, k1000].mean()), 2),
          "| neighbour dB:", round(float(db[:, k1000 - 3].mean()), 2))
