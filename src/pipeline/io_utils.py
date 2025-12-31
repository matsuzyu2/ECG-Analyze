from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
import pandas as pd

from .config import Config, default_config


TIME_CANDIDATES: Tuple[str, ...] = ("Time (s)", "time", "Time")
ECG_CANDIDATES: Tuple[str, ...] = ("ECG (uV)", "ecg", "ECG")


def _pick_column(columns: Iterable[str], candidates: Tuple[str, ...]) -> str:
    lowered = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    raise KeyError(f"Required column not found. Candidates: {candidates}; columns: {list(columns)}")


def load_ecg_segment(path: Path, cfg: Config | None = None, normalize_time: bool = True) -> tuple[np.ndarray, np.ndarray, Config]:
    cfg = cfg or default_config()
    df = pd.read_csv(path)
    time_col = _pick_column(df.columns, TIME_CANDIDATES)
    ecg_col = _pick_column(df.columns, ECG_CANDIDATES)

    time = pd.to_numeric(df[time_col], errors="coerce").to_numpy(dtype=float)
    ecg = pd.to_numeric(df[ecg_col], errors="coerce").to_numpy(dtype=float)

    mask = np.isfinite(time) & np.isfinite(ecg)
    time = time[mask]
    ecg = ecg[mask]

    if normalize_time and len(time) > 0:
        time = time - time[0]

    sr = cfg.sampling_rate if cfg.sampling_rate else infer_sampling_rate(time)
    cfg = Config(
        sampling_rate=sr,
        bp_low_hz=cfg.bp_low_hz,
        bp_high_hz=cfg.bp_high_hz,
        bp_order=cfg.bp_order,
        mad_k=cfg.mad_k,
        rr_min_ms=cfg.rr_min_ms,
        rr_max_ms=cfg.rr_max_ms,
        resample_rate_hz=cfg.resample_rate_hz,
        welch_window_sec=cfg.welch_window_sec,
        welch_overlap=cfg.welch_overlap,
        min_quality=cfg.min_quality,
    )
    return time, ecg, cfg


def infer_sampling_rate(time_sec: np.ndarray) -> float:
    if len(time_sec) < 2:
        raise ValueError("Not enough samples to infer sampling rate")
    diffs = np.diff(time_sec)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) == 0:
        raise ValueError("Cannot infer sampling rate; non-positive diffs")
    median_dt = np.median(diffs)
    return float(1.0 / median_dt)
