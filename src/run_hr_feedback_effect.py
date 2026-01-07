#!/usr/bin/env python3
"""HR Feedback: 前半/後半ウィンドウ比較（デフォルト: 各3分）

前提:
- Data/Processed/{session_id}/split_segments/ に分割済みセグメントCSVがある
- "Session" を含むファイル（複数可）が「心拍フィードバック」中のECGデータ

本スクリプトは、各 Session セグメントについて
- 前半 window_sec 秒
- 後半 window_sec 秒
のHR/HRV指標を算出し、後半−前半の差分も併記してCSVに保存します。

Usage:
  # 全セッションを対象（デフォルト: window=180秒）
  python src/run_hr_feedback_effect.py

  # 特定セッションのみ
  python src/run_hr_feedback_effect.py --session 251216_TK

  # ウィンドウ長を変更（例: 2分）
  python src/run_hr_feedback_effect.py --window-sec 120

Output:
  Results/stats/hr_feedback_effect_{window}s.csv

Notes:
- split_by_annotation.py が付与するパディング（端のフィルタアーチファクト対策）が
  存在する場合は、まず全体をフィルタリングしてパディングを除去してから、
  前半/後半ウィンドウを切り出します（内部境界のフィルタアーチファクト回避）。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure this script works when executed from any CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis_pipeline.config import Config
from analysis_pipeline.io_utils import get_available_sessions, list_segment_files, load_segment_csv
from analysis_pipeline.preprocess import filter_ecg
from analysis_pipeline.rpeak import detect_rpeaks
from analysis_pipeline.hrv import compute_hrv_metrics, HRVMetrics


def _is_session_file(path: Path) -> bool:
    return "session" in path.stem.lower()


def _trim_padding_if_present(
    ecg: np.ndarray,
    time: np.ndarray,
    segment_data,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    notes: List[str] = []

    if not getattr(segment_data, "has_padding", False):
        return ecg, time, notes

    start_idx = int(getattr(segment_data, "original_start_idx", 0))
    end_idx_inclusive = int(getattr(segment_data, "original_end_idx", len(ecg) - 1))
    end_idx = end_idx_inclusive + 1

    if start_idx < 0 or end_idx > len(ecg) or start_idx >= end_idx:
        notes.append(
            f"⚠ padding bounds invalid [{start_idx}:{end_idx}] for len={len(ecg)}; using full segment"
        )
        return ecg, time, notes

    notes.append(
        f"✓ padding trimmed [{start_idx}:{end_idx}] (len={end_idx-start_idx})"
    )
    return ecg[start_idx:end_idx], time[start_idx:end_idx], notes


def _slice_windows(
    n_samples: int,
    fs: int,
    window_sec: int,
) -> Tuple[slice, slice, List[str]]:
    notes: List[str] = []

    window_samples = int(round(window_sec * fs))
    if window_samples <= 1:
        raise ValueError(f"window_sec too small: {window_sec}")

    if n_samples <= 2:
        return slice(0, 0), slice(0, 0), ["✗ segment too short"]

    early = slice(0, min(n_samples, window_samples))
    late_start = max(0, n_samples - window_samples)
    late = slice(late_start, n_samples)

    early_len = early.stop - early.start
    late_len = late.stop - late.start

    if early_len < window_samples:
        notes.append(
            f"⚠ early window shorter than requested ({early_len/fs:.1f}s < {window_sec}s)"
        )
    if late_len < window_samples:
        notes.append(
            f"⚠ late window shorter than requested ({late_len/fs:.1f}s < {window_sec}s)"
        )

    # overlap check
    if late.start < early.stop:
        overlap = early.stop - late.start
        notes.append(
            f"⚠ windows overlap by {overlap/fs:.1f}s (segment duration={n_samples/fs:.1f}s)"
        )

    return early, late, notes


def _prefix_dict(prefix: str, d: Dict[str, object]) -> Dict[str, object]:
    return {f"{prefix}{k}": v for k, v in d.items()}


def _hrv_to_flat(hrv: HRVMetrics) -> Dict[str, object]:
    return hrv.to_flat_dict()


_CORE_METRICS: Tuple[str, ...] = (
    "time_mean_hr",
    "time_rmssd",
    "freq_lf_hf_ratio",
)


def _extract_core_metrics(flat: Dict[str, object]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key in _CORE_METRICS:
        value = flat.get(key)
        try:
            out[key] = float(value)
        except Exception:
            out[key] = float("nan")
    return out


def _compute_window_metrics(
    *,
    ecg_filtered: np.ndarray,
    time: np.ndarray,
    fs: int,
    window_slice: slice,
    segment_name: str,
    session_id: str,
    config: Config,
) -> Tuple[Dict[str, object], List[str]]:
    notes: List[str] = []

    ecg_w = ecg_filtered[window_slice]
    time_w = time[window_slice]

    duration_sec = float(len(ecg_w) / fs) if fs > 0 else float("nan")

    if len(ecg_w) < max(5, int(fs * 3)):
        notes.append("✗ window too short for robust detection")

    detection = detect_rpeaks(ecg_w, fs=fs, time=time_w, config=config)
    notes.append(f"✓ peaks={detection.n_peaks}, quality={detection.quality_score:.2f}")
    notes.extend(detection.quality_notes)

    hrv = compute_hrv_metrics(
        peak_times=np.asarray(detection.peak_times, dtype=float),
        segment_name=segment_name,
        session_id=session_id,
        duration_sec=duration_sec,
        config=config,
    )

    flat = _hrv_to_flat(hrv)
    core = _extract_core_metrics(flat)
    return core, notes


def process_session(
    session_id: str,
    *,
    window_sec: int,
    config: Config,
    verbose: bool,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    segment_files = list_segment_files(session_id, config)
    session_files = [p for p in segment_files if _is_session_file(p)]

    if verbose:
        print(f"\nSession: {session_id}")
        print(f"  Session segments: {len(session_files)}")

    if not session_files:
        return rows

    for segment_path in session_files:
        seg_name = segment_path.stem

        if verbose:
            print(f"  - {seg_name}")

        try:
            segment_data = load_segment_csv(segment_path, session_id, config)

            ecg_raw = segment_data.ecg
            time = segment_data.time
            fs = int(segment_data.fs)

            # Filter full segment first, then trim padding (if present)
            ecg_filtered = filter_ecg(ecg_raw, fs=fs, config=config)
            ecg_filtered, time_trimmed, pad_notes = _trim_padding_if_present(
                ecg_filtered, time, segment_data
            )

            # Also align time array with trimming
            # (Note: _trim_padding_if_present already applied to time via time_trimmed)
            time = time_trimmed

            early_slice, late_slice, win_notes = _slice_windows(
                n_samples=len(ecg_filtered),
                fs=fs,
                window_sec=window_sec,
            )

            # Compute HRV for early/late windows
            early_core, _ = _compute_window_metrics(
                ecg_filtered=ecg_filtered,
                time=time,
                fs=fs,
                window_slice=early_slice,
                segment_name=f"{seg_name}__early_{window_sec}s",
                session_id=session_id,
                config=config,
            )
            late_core, _ = _compute_window_metrics(
                ecg_filtered=ecg_filtered,
                time=time,
                fs=fs,
                window_slice=late_slice,
                segment_name=f"{seg_name}__late_{window_sec}s",
                session_id=session_id,
                config=config,
            )

            # Build single-row comparison
            base: Dict[str, object] = {
                "session_id": session_id,
                "segment_name": seg_name,
                "window_sec": int(window_sec),
            }

            out: Dict[str, object] = {
                **base,
                **_prefix_dict("early_", early_core),
                **_prefix_dict("late_", late_core),
            }

            # Diffs (late - early)
            for c in _CORE_METRICS:
                try:
                    out[f"diff_{c}"] = float(out.get(f"late_{c}")) - float(out.get(f"early_{c}"))
                except Exception:
                    out[f"diff_{c}"] = float("nan")

            # Percent change: (late-early)/early * 100
            for c in _CORE_METRICS:
                try:
                    e = float(out.get(f"early_{c}"))
                    l = float(out.get(f"late_{c}"))
                    if np.isfinite(e) and np.isfinite(l) and abs(e) > 1e-12:
                        out[f"pct_{c}"] = (l - e) / e * 100.0
                    else:
                        out[f"pct_{c}"] = float("nan")
                except Exception:
                    out[f"pct_{c}"] = float("nan")

            # Enforce minimal schema order (no extra columns)
            ordered_keys = [
                "session_id",
                "segment_name",
                "window_sec",
                "early_time_mean_hr",
                "late_time_mean_hr",
                "diff_time_mean_hr",
                "pct_time_mean_hr",
                "early_time_rmssd",
                "late_time_rmssd",
                "diff_time_rmssd",
                "pct_time_rmssd",
                "early_freq_lf_hf_ratio",
                "late_freq_lf_hf_ratio",
                "diff_freq_lf_hf_ratio",
                "pct_freq_lf_hf_ratio",
            ]
            rows.append({k: out.get(k, float("nan")) for k in ordered_keys})

        except Exception as e:
            if verbose:
                print(f"    ✗ ERROR: {e}")

            # Keep CSV schema fixed (no error column)
            rows.append(
                {
                    "session_id": session_id,
                    "segment_name": seg_name,
                    "window_sec": int(window_sec),
                    "early_time_mean_hr": float("nan"),
                    "late_time_mean_hr": float("nan"),
                    "diff_time_mean_hr": float("nan"),
                    "pct_time_mean_hr": float("nan"),
                    "early_time_rmssd": float("nan"),
                    "late_time_rmssd": float("nan"),
                    "diff_time_rmssd": float("nan"),
                    "pct_time_rmssd": float("nan"),
                    "early_freq_lf_hf_ratio": float("nan"),
                    "late_freq_lf_hf_ratio": float("nan"),
                    "diff_freq_lf_hf_ratio": float("nan"),
                    "pct_freq_lf_hf_ratio": float("nan"),
                }
            )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HR Feedback(Session) 前半/後半のHRV比較（デフォルト各3分）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--session",
        "-s",
        type=str,
        default=None,
        help="特定セッションのみ対象（例: 251216_TK）。未指定なら全セッションを走査",
    )

    parser.add_argument(
        "--window-sec",
        type=int,
        default=180,
        help="前半/後半として切り出す秒数（デフォルト: 180秒=3分）",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="進捗表示を抑制",
    )

    args = parser.parse_args()

    config = Config()
    verbose = not args.quiet

    if args.window_sec <= 0:
        raise SystemExit("--window-sec must be > 0")

    if args.session:
        sessions = [args.session]
    else:
        sessions = get_available_sessions(config)

    if not sessions:
        print("No sessions found under Data/Processed/*/split_segments")
        return 1

    all_rows: List[Dict[str, object]] = []
    for sid in sessions:
        try:
            rows = process_session(sid, window_sec=args.window_sec, config=config, verbose=verbose)
            all_rows.extend(rows)
        except Exception as e:
            all_rows.append({"session_id": sid, "error": str(e), "window_sec": int(args.window_sec)})
            if verbose:
                print(f"\nSession: {sid} ✗ ERROR: {e}")

    if not all_rows:
        print("No Session segments found.")
        return 0

    df = pd.DataFrame(all_rows)

    # Fixed minimal output columns
    column_order = [
        "session_id",
        "segment_name",
        "window_sec",
        "early_time_mean_hr",
        "late_time_mean_hr",
        "diff_time_mean_hr",
        "pct_time_mean_hr",
        "early_time_rmssd",
        "late_time_rmssd",
        "diff_time_rmssd",
        "pct_time_rmssd",
        "early_freq_lf_hf_ratio",
        "late_freq_lf_hf_ratio",
        "diff_freq_lf_hf_ratio",
        "pct_freq_lf_hf_ratio",
    ]
    df = df[column_order]

    out_dir = config.get_stats_dir()
    out_path = out_dir / f"hr_feedback_effect_{int(args.window_sec)}s.csv"
    df.to_csv(out_path, index=False)

    if verbose:
        print("\n" + "=" * 60)
        print("HR Feedback Effect Summary")
        print("=" * 60)
        print(f"Rows: {len(df)}")
        print(f"Saved: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
