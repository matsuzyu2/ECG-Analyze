from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from .config import Config, default_config
from .io_utils import load_ecg_segment
from .preprocess import filter_and_detrend, noise_metrics
from .rpeak_detect import detect_rpeaks
from .rr_clean import clean_rr, rr_intervals_ms
from .hrv_metrics import compute_hrv
from .qc_report import build_qc_figure, save_html


def process_file(path: Path, output_dir: Path, cfg: Config) -> dict:
    time, ecg, cfg = load_ecg_segment(path, cfg)

    filt = filter_and_detrend(ecg, cfg)
    noise = noise_metrics(ecg)

    peak_result = detect_rpeaks(filt, cfg)
    peaks = peak_result["peaks"]
    quality = peak_result["quality"]

    rr_raw = rr_intervals_ms(peaks, cfg.sampling_rate)
    rr_clean_result = clean_rr(rr_raw, cfg)

    hrv = compute_hrv(rr_clean_result["interp_rr_ms"], cfg)

    reasons = []
    if not np.isfinite(quality):
        reasons.append("quality_nan")
    elif quality < cfg.min_quality:
        reasons.append("quality_below_threshold")
    if not hrv:
        reasons.append("hrv_not_computed")
    is_valid = not reasons

    rri_df = pd.DataFrame(
        {
            "rr_ms_raw": rr_clean_result["rr_ms_raw"],
            "rr_ms_clean": rr_clean_result["rr_ms_clean"],
            "rr_ms_interp": rr_clean_result["interp_rr_ms"],
            "outlier": rr_clean_result["outlier_mask"],
        }
    )

    seg_name = path.stem
    rri_path = output_dir / f"{seg_name}_rri.csv"
    rri_path.parent.mkdir(parents=True, exist_ok=True)
    rri_df.to_csv(rri_path, index=False)

    hrv_row = {
        "segment": seg_name,
        "quality": quality,
        "is_valid": is_valid,
        "reject_reason": "|".join(reasons),
        **noise,
        **hrv,
    }

    qc_fig = build_qc_figure(time, ecg, filt, peaks, rr_clean_result["interp_rr_ms"], cfg)
    qc_path = output_dir / "figures" / f"{seg_name}_qc.html"
    save_html(qc_fig, qc_path)

    return hrv_row


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch ECG HRV pipeline for segmented files.")
    parser.add_argument("input_dir", type=Path, help="Directory containing segmented ECG CSVs")
    parser.add_argument("--output-dir", type=Path, default=None, help="Results directory (default: Results/<input_dir_name>)")
    args = parser.parse_args()

    cfg = default_config()

    input_dir: Path = args.input_dir
    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")

    output_dir = args.output_dir or Path("Results") / input_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    hrv_rows: List[dict] = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        print(f"Processing {csv_path.name} ...")
        hrv_rows.append(process_file(csv_path, output_dir, cfg))

    summary = pd.DataFrame(hrv_rows)
    summary_path = output_dir / "hrv_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"✓ Done. Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
