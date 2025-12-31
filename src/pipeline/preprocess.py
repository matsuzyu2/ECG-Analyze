from __future__ import annotations

import numpy as np
import neurokit2 as nk

from .config import Config


def filter_and_detrend(ecg: np.ndarray, cfg: Config) -> np.ndarray:
    # IIR butterworth with filtfilt; zero-phase
    filtered = nk.signal_filter(
        ecg,
        sampling_rate=cfg.sampling_rate,
        lowcut=cfg.bp_low_hz,
        highcut=cfg.bp_high_hz,
        order=cfg.bp_order,
        method="butterworth",
    )
    return nk.signal_detrend(filtered, method="polynomial", order=1)


def noise_metrics(ecg: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(ecg)
    if not finite.any():
        return {"nan_frac": 1.0, "clip_frac": 1.0, "rms": 0.0}

    x = ecg[finite]
    nan_frac = 1.0 - (len(x) / len(ecg))
    low, high = np.percentile(x, [1, 99])
    clip_mask = (x <= low) | (x >= high)
    clip_frac = float(np.mean(clip_mask))
    rms = float(np.sqrt(np.mean(np.square(x - np.mean(x)))))
    return {"nan_frac": nan_frac, "clip_frac": clip_frac, "rms": rms}
