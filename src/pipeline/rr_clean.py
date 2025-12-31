from __future__ import annotations

import numpy as np

from .config import Config


MAD_SCALE = 1.4826


def rr_intervals_ms(peaks: np.ndarray, sampling_rate: float) -> np.ndarray:
    if len(peaks) < 2:
        return np.array([], dtype=float)
    rr_samples = np.diff(peaks)
    return rr_samples / sampling_rate * 1000.0


def clean_rr(rr_ms: np.ndarray, cfg: Config) -> dict[str, np.ndarray]:
    if rr_ms.size == 0:
        return {
            "rr_ms_raw": rr_ms,
            "rr_ms_clean": rr_ms,
            "outlier_mask": np.array([], dtype=bool),
            "interp_rr_ms": rr_ms,
        }

    physiologic = (rr_ms >= cfg.rr_min_ms) & (rr_ms <= cfg.rr_max_ms)

    med = float(np.median(rr_ms[physiologic])) if physiologic.any() else float(np.median(rr_ms))
    mad = float(np.median(np.abs(rr_ms - med))) if rr_ms.size else 0.0
    threshold = med + cfg.mad_k * MAD_SCALE * mad if mad > 0 else cfg.rr_max_ms

    outlier_mask = (~physiologic) | (np.abs(rr_ms - med) > threshold)

    rr_clean = rr_ms.copy()
    rr_clean[outlier_mask] = np.nan

    # Interpolate NaN gaps linearly on index axis.
    rr_interp = _interpolate_nan(rr_clean)

    return {
        "rr_ms_raw": rr_ms,
        "rr_ms_clean": rr_clean,
        "outlier_mask": outlier_mask,
        "interp_rr_ms": rr_interp,
    }


def _interpolate_nan(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    idx = np.arange(x.size)
    good = np.isfinite(x)
    if good.sum() < 2:
        return np.full_like(x, fill_value=np.nan)
    return np.interp(idx, idx[good], x[good])
