"""
I/O utilities for ECG analysis pipeline.

Handles:
- CSV loading with automatic unit conversion (µV → mV)
- Peak information JSON save/load
- Intermediate file management
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .config import Config, default_config


@dataclass
class SegmentData:
    """Container for loaded segment data."""
    ecg: np.ndarray           # ECG signal in mV
    time: np.ndarray          # Time in seconds
    fs: int                   # Sampling rate
    segment_name: str         # Segment identifier
    session_id: str           # Session identifier
    was_converted: bool       # True if µV→mV conversion was applied
    original_mean_abs: float  # Mean absolute value before conversion
    
    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        return len(self.ecg) / self.fs
    
    @property
    def n_samples(self) -> int:
        """Number of samples."""
        return len(self.ecg)


@dataclass
class PeakInfo:
    """Container for R-peak detection results."""
    segment_name: str
    session_id: str
    peak_indices: List[int]          # Sample indices of R-peaks
    peak_times: List[float]          # Time in seconds of R-peaks
    is_inverted: bool                # True if signal was inverted
    skewness: float                  # Original signal skewness
    was_converted: bool              # True if µV→mV conversion applied
    fs: int                          # Sampling rate
    n_samples: int                   # Total samples in segment
    detection_method: str            # Detection algorithm used
    processed_at: str                # ISO timestamp
    quality_notes: List[str]         # Quality warnings/notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PeakInfo":
        """Create PeakInfo from dictionary."""
        return cls(**data)


def load_segment_csv(
    csv_path: Path,
    session_id: str,
    config: Config = default_config,
) -> SegmentData:
    """
    Load ECG segment from CSV with automatic unit conversion.
    
    Critical: Always convert ECG values to mV.
    This project assumes the sensor exports ECG in µV.
    Therefore, we always apply: ecg_mV = ecg_uV / 1000.
    
    Parameters
    ----------
    csv_path : Path
        Path to the segment CSV file.
    session_id : str
        Session identifier for metadata.
    config : Config
        Pipeline configuration.
    
    Returns
    -------
    SegmentData
        Loaded and converted ECG data.
    
    Raises
    ------
    ValueError
        If required columns are missing.
    FileNotFoundError
        If CSV file does not exist.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Segment file not found: {csv_path}")
    
    # Load CSV
    df = pd.read_csv(csv_path)
    
    # Identify ECG column (handle variations)
    ecg_column = None
    for col in df.columns:
        if "ExGa" in col:
            ecg_column = col
            break
    
    if ecg_column is None:
        raise ValueError(f"No EXGA column found in {csv_path}. Columns: {list(df.columns)}")
    
    # Extract ECG values (force a real NumPy array for type-safety)
    ecg_raw = df[ecg_column].to_numpy(dtype=np.float64, copy=True)
    
    # Handle NaN values
    if np.any(np.isnan(ecg_raw)):
        nan_count = int(np.sum(np.isnan(ecg_raw)))
        print(f"  ⚠ Warning: {nan_count} NaN values found, interpolating...")
        ecg_raw = (
            pd.Series(ecg_raw)
            .interpolate(method="linear")
            .bfill()
            .ffill()
            .to_numpy(dtype=np.float64)
        )
    
    # Keep for logging/QA purposes (value before conversion)
    original_mean_abs = np.abs(ecg_raw).mean()

    # Unit conversion: µV → mV 
    if "uV" in ecg_column:
        ecg = ecg_raw / 1000.0
        was_converted = True
    else:
        ecg = ecg_raw
        was_converted = False
    
    # Extract time column
    time_column = None
    for col in df.columns:
        if "time" in col.lower() and "stamp" not in col.lower():
            time_column = col
            break
    
    if time_column is not None:
        time = df[time_column].to_numpy(dtype=np.float64, copy=True)
    else:
        # Generate time array from sampling rate
        time = np.arange(len(ecg), dtype=np.float64) / config.SAMPLING_RATE
    
    # Extract segment name from filename
    segment_name = csv_path.stem
    
    return SegmentData(
        ecg=ecg,
        time=time,
        fs=config.SAMPLING_RATE,
        segment_name=segment_name,
        session_id=session_id,
        was_converted=was_converted,
        original_mean_abs=original_mean_abs,
    )


def save_peaks_json(
    peak_info: PeakInfo,
    output_path: Path,
) -> None:
    """
    Save peak detection results to JSON file.
    
    Parameters
    ----------
    peak_info : PeakInfo
        Peak detection results and metadata.
    output_path : Path
        Path for output JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(peak_info.to_dict(), f, indent=2, ensure_ascii=False)


def load_peaks_json(json_path: Path) -> PeakInfo:
    """
    Load peak detection results from JSON file.
    
    Parameters
    ----------
    json_path : Path
        Path to peaks JSON file.
    
    Returns
    -------
    PeakInfo
        Loaded peak information.
    
    Raises
    ------
    FileNotFoundError
        If JSON file does not exist.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"Peaks file not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return PeakInfo.from_dict(data)


def list_segment_files(
    session_id: str,
    config: Config = default_config,
) -> List[Path]:
    """
    List all segment CSV files for a session.
    
    Parameters
    ----------
    session_id : str
        Session identifier.
    config : Config
        Pipeline configuration.
    
    Returns
    -------
    List[Path]
        Sorted list of segment file paths.
    """
    segments_dir = config.get_segments_dir(session_id)
    
    if not segments_dir.exists():
        raise FileNotFoundError(f"Segments directory not found: {segments_dir}")
    
    segment_files = sorted(segments_dir.glob("*.csv"))
    
    if not segment_files:
        raise FileNotFoundError(f"No CSV files found in: {segments_dir}")
    
    return segment_files


def list_peaks_files(
    session_id: str,
    config: Config = default_config,
) -> List[Path]:
    """
    List all peaks JSON files for a session.
    
    Parameters
    ----------
    session_id : str
        Session identifier.
    config : Config
        Pipeline configuration.
    
    Returns
    -------
    List[Path]
        Sorted list of peaks file paths.
    """
    results_dir = config.get_session_results_dir(session_id)
    peaks_files = sorted(results_dir.glob(f"{config.PEAKS_PREFIX}*.json"))
    return peaks_files


def get_available_sessions(config: Config = default_config) -> List[str]:
    """
    Get list of available session IDs with processed segments.
    
    Parameters
    ----------
    config : Config
        Pipeline configuration.
    
    Returns
    -------
    List[str]
        List of session identifiers.
    """
    processed_dir = config.get_data_dir() / config.PROCESSED_SUBDIR
    
    if not processed_dir.exists():
        return []
    
    sessions = []
    for session_dir in processed_dir.iterdir():
        if session_dir.is_dir():
            segments_dir = session_dir / config.SEGMENTS_SUBDIR
            if segments_dir.exists() and list(segments_dir.glob("*.csv")):
                sessions.append(session_dir.name)
    
    return sorted(sessions)
