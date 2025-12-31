from __future__ import annotations

import numpy as np
import neurokit2 as nk

from .config import Config


def compute_hrv(rr_ms: np.ndarray, cfg: Config) -> dict[str, float]:
    # Remove NaN before passing to NK
    clean = rr_ms[np.isfinite(rr_ms)]
    if clean.size < 2:
        return {}

    time_metrics = nk.hrv_time(rri=clean, sampling_rate=1000, show=False).iloc[0].to_dict()

    freq_metrics = nk.hrv_frequency(
        rri=clean,
        sampling_rate=cfg.resample_rate_hz,
        method="welch",
        show=False,
    ).iloc[0].to_dict()

    return {**time_metrics, **freq_metrics}
