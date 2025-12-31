from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import signal

from .config import Config


def build_qc_figure(
    time: np.ndarray,
    ecg: np.ndarray,
    filtered: np.ndarray,
    peaks: np.ndarray,
    rr_interp_ms: np.ndarray,
    cfg: Config,
) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=False, subplot_titles=("ECG with R-peaks", "RR tachogram", "Welch PSD"))

    fig.add_trace(go.Scatter(x=time, y=ecg, mode="lines", name="ECG raw"), row=1, col=1)
    fig.add_trace(go.Scatter(x=time, y=filtered, mode="lines", name="ECG filtered"), row=1, col=1)
    if peaks.size:
        fig.add_trace(
            go.Scatter(
                x=time[peaks],
                y=filtered[peaks],
                mode="markers",
                marker=dict(color="red", size=6),
                name="R-peaks",
            ),
            row=1,
            col=1,
        )

    rr_time = _rr_time_axis(rr_interp_ms)
    fig.add_trace(go.Scatter(x=rr_time, y=rr_interp_ms, mode="lines+markers", name="RR (ms)"), row=2, col=1)

    freqs, psd = _welch_rr(rr_interp_ms, cfg)
    fig.add_trace(go.Scatter(x=freqs, y=psd, mode="lines", name="PSD"), row=3, col=1)

    fig.update_layout(height=900, showlegend=True)
    fig.update_xaxes(title_text="Time (s)", row=1, col=1)
    fig.update_yaxes(title_text="uV", row=1, col=1)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    fig.update_yaxes(title_text="RR (ms)", row=2, col=1)
    fig.update_xaxes(title_text="Hz", row=3, col=1)
    fig.update_yaxes(title_text="Power", row=3, col=1, type="log")
    return fig


def save_html(fig: go.Figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))


def _rr_time_axis(rr_ms: np.ndarray) -> np.ndarray:
    if rr_ms.size == 0:
        return np.array([])
    cumulative = np.cumsum(rr_ms) / 1000.0
    return cumulative - cumulative[0]


def _welch_rr(rr_ms: np.ndarray, cfg: Config) -> tuple[np.ndarray, np.ndarray]:
    if rr_ms.size < 4:
        return np.array([]), np.array([])

    t = _rr_time_axis(rr_ms)
    if t.size == 0:
        return np.array([]), np.array([])

    # Resample RR to evenly spaced grid for Welch
    grid = np.arange(0, t[-1], 1.0 / cfg.resample_rate_hz)
    rr_interp = np.interp(grid, t, rr_ms) if grid.size else np.array([])
    if rr_interp.size < 4:
        return np.array([]), np.array([])

    nperseg = min(len(rr_interp), int(cfg.welch_window_sec * cfg.resample_rate_hz))
    nperseg = max(4, nperseg)

    freqs, psd = signal.welch(
        rr_interp,
        fs=cfg.resample_rate_hz,
        nperseg=nperseg,
        noverlap=int(cfg.welch_overlap * nperseg) if nperseg > 1 else 0,
        detrend="constant",
        scaling="density",
        window="hann",
    )
    return freqs, psd
