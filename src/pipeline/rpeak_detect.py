from __future__ import annotations

import numpy as np
import neurokit2 as nk

from . import compat  # ensures NumPy compatibility shims are applied
from .config import Config


def detect_rpeaks(ecg: np.ndarray, cfg: Config) -> dict[str, np.ndarray | float]:
    # nk.ecg_peaks expects cleaned signal; apply nk.ecg_clean for robustness even after filtering
    cleaned = nk.ecg_clean(ecg, sampling_rate=cfg.sampling_rate, method="neurokit")
    peaks, info = nk.ecg_peaks(cleaned, sampling_rate=cfg.sampling_rate)

    peak_indices = np.where(peaks.get("ECG_R_Peaks", []))[0]
    raw_quality = nk.ecg_quality(cleaned, sampling_rate=cfg.sampling_rate, method="zhao2018")
    quality = _quality_score(raw_quality)

    return {
        "cleaned": cleaned,
        "peaks": peak_indices,
        "quality": quality,
        "info": info,
    }


def _quality_score(raw) -> float:
    # NeuroKit2 may return strings like "Unacceptable"; map to numeric.
    if isinstance(raw, (int, float, np.floating)):
        return float(raw)

    mapping = {
        "unacceptable": 0.0,
        "barely acceptable": 0.25,
        "acceptable": 0.5,
        "excellent": 1.0,
    }
    if isinstance(raw, str):
        return mapping.get(raw.lower(), float("nan"))

    return float("nan")
