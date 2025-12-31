from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Sampling
    sampling_rate: float = 130.0  # Hz; override per file if known

    # Filtering
    bp_low_hz: float = 0.5
    bp_high_hz: float = 40.0
    bp_order: int = 4

    # RR cleaning
    mad_k: float = 3.0
    rr_min_ms: float = 300.0
    rr_max_ms: float = 2000.0

    # Frequency domain
    resample_rate_hz: float = 4.0  # for interpolation before Welch
    welch_window_sec: float = 60.0
    welch_overlap: float = 0.5

    # Quality
    min_quality: float = 0.5  # NeuroKit2 quality score threshold


def default_config() -> Config:
    return Config()
