from __future__ import annotations

import numpy as np
import neurokit2 as nk

from .config import Config


def compute_hrv(rr_ms: np.ndarray, cfg: Config) -> dict[str, float]:
    # Remove NaN before passing to NK
    clean = rr_ms[np.isfinite(rr_ms)]
    if clean.size < 2:
        return {}

    # Reconstruct peak locations (in ms) to satisfy peaks input
    peaks_ms = np.r_[0, np.cumsum(clean)]

    time_metrics = nk.hrv_time(peaks=peaks_ms, sampling_rate=1000, show=False).iloc[0].to_dict()

    freq_metrics = nk.hrv_frequency(
        peaks=peaks_ms,
        sampling_rate=1000,
        method="welch",
        show=False,
    ).iloc[0].to_dict()

    return {**time_metrics, **freq_metrics}
