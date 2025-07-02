"""Utility functions for ViSQOL-Py."""

import os
import csv
from pathlib import Path
from typing import List, Tuple, Union, Optional

import numpy as np

try:
    import librosa
    import soundfile as sf
except ImportError as e:
    raise ImportError(
        "Required audio processing libraries not found. "
        "Please install with: pip install librosa soundfile"
    ) from e

from .visqol import ViSQOLResult


def load_audio(
    file_path: Union[str, Path],
    sample_rate: Optional[int] = None,
    mono: bool = True
) -> Tuple[np.ndarray, int]:
    """
    Load audio file using librosa.
    
    Args:
        file_path: Path to audio file
        sample_rate: Target sample rate (None to keep original)
        mono: Convert to mono if True
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio_data, sr = librosa.load(str(file_path), sr=sample_rate, mono=mono)
    return audio_data, sr


def save_audio(
    audio_data: np.ndarray,
    file_path: Union[str, Path],
    sample_rate: int
) -> None:
    """
    Save audio data to file.
    
    Args:
        audio_data: Audio data array
        file_path: Output file path
        sample_rate: Sample rate
    """
    sf.write(str(file_path), audio_data, sample_rate)


def load_batch_csv(csv_path: Union[str, Path]) -> List[Tuple[str, str]]:
    """
    Load batch processing CSV file.
    
    Expected format:
    reference,degraded
    ref1.wav,deg1.wav
    ref2.wav,deg2.wav
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of (reference_path, degraded_path) tuples
    """
    file_pairs = []
    
    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ref_path = row.get('reference', '').strip()
            deg_path = row.get('degraded', '').strip()
            
            if ref_path and deg_path:
                file_pairs.append((ref_path, deg_path))
    
    return file_pairs


def save_results(
    results: List[ViSQOLResult],
    output_path: Union[str, Path],
    format: str = 'csv'
) -> None:
    """
    Save ViSQOL results to file.
    
    Args:
        results: List of ViSQOL results
        output_path: Output file path
        format: Output format ('csv' or 'json')
    """
    if format.lower() == 'csv':
        _save_results_csv(results, output_path)
    elif format.lower() == 'json':
        _save_results_json(results, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _save_results_csv(results: List[ViSQOLResult], output_path: Union[str, Path]) -> None:
    """Save results as CSV."""
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow(['reference', 'degraded', 'moslqo', 'vnsim'])
        
        # Data
        for result in results:
            writer.writerow([
                result.reference_path or '',
                result.degraded_path or '',
                f"{result.moslqo:.6f}",
                f"{result.vnsim:.6f}"
            ])


def _save_results_json(results: List[ViSQOLResult], output_path: Union[str, Path]) -> None:
    """Save results as JSON."""
    import json
    
    results_data = []
    for result in results:
        results_data.append({
            'reference_path': result.reference_path,
            'degraded_path': result.degraded_path,
            'moslqo': result.moslqo,
            'vnsim': result.vnsim,
            'fvnsim': result.fvnsim,
            'center_freq_bands': result.center_freq_bands,
        })
    
    with open(output_path, 'w') as jsonfile:
        json.dump(results_data, jsonfile, indent=2)


def validate_audio_files(file_paths: List[str]) -> List[str]:
    """
    Validate that audio files exist and are readable.
    
    Args:
        file_paths: List of file paths to validate
        
    Returns:
        List of valid file paths
    """
    valid_paths = []
    
    for file_path in file_paths:
        if os.path.isfile(file_path):
            try:
                # Try to load a small portion to validate format
                librosa.load(file_path, sr=None, duration=0.1)
                valid_paths.append(file_path)
            except Exception as e:
                print(f"Warning: Could not load {file_path}: {e}")
        else:
            print(f"Warning: File not found: {file_path}")
    
    return valid_paths


def resample_audio(
    audio_data: np.ndarray,
    orig_sr: int,
    target_sr: int
) -> np.ndarray:
    """
    Resample audio data.
    
    Args:
        audio_data: Input audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate
        
    Returns:
        Resampled audio data
    """
    if orig_sr == target_sr:
        return audio_data
    
    return librosa.resample(audio_data, orig_sr=orig_sr, target_sr=target_sr)


def compute_audio_stats(audio_data: np.ndarray, sample_rate: int) -> dict:
    """
    Compute basic audio statistics.
    
    Args:
        audio_data: Audio data array
        sample_rate: Sample rate
        
    Returns:
        Dictionary with audio statistics
    """
    return {
        'duration': len(audio_data) / sample_rate,
        'sample_rate': sample_rate,
        'num_samples': len(audio_data),
        'rms': np.sqrt(np.mean(audio_data**2)),
        'max_amplitude': np.max(np.abs(audio_data)),
        'mean_amplitude': np.mean(np.abs(audio_data)),
    }