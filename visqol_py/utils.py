"""Utility functions for ViSQOL-Py."""

import os
import csv
from pathlib import Path
from typing import List, Tuple, Union, Optional

import numpy as np

import struct
import wave

from .visqol import ViSQOLResult


def load_audio(
    file_path: Union[str, Path],
    sample_rate: Optional[int] = None,
    mono: bool = True
) -> Tuple[np.ndarray, int]:
    """
    Load WAV audio file using Python's built-in wave module.
    
    Args:
        file_path: Path to WAV file
        sample_rate: Target sample rate (None to keep original)
        mono: Convert to mono if True (always True for WAV loading)
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio_data, orig_sr = _load_wav_file(str(file_path))
    
    # Resample if needed
    if sample_rate is not None and orig_sr != sample_rate:
        audio_data = resample_audio(audio_data, orig_sr, sample_rate)
        orig_sr = sample_rate
    
    return audio_data, orig_sr


def save_audio(
    audio_data: np.ndarray,
    file_path: Union[str, Path],
    sample_rate: int
) -> None:
    """
    Save audio data to WAV file.
    
    Args:
        audio_data: Audio data array
        file_path: Output WAV file path  
        sample_rate: Sample rate
    """
    _save_wav_file(audio_data, str(file_path), sample_rate)


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
                # Try to read WAV file info to validate format
                with wave.open(file_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    if frames > 0:  # Valid WAV file
                        valid_paths.append(file_path)
                    else:
                        print(f"Warning: Empty WAV file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not load WAV file {file_path}: {e}")
        else:
            print(f"Warning: File not found: {file_path}")
    
    return valid_paths


def resample_audio(
    audio_data: np.ndarray,
    orig_sr: int,
    target_sr: int
) -> np.ndarray:
    """
    Resample audio data using linear interpolation.
    
    Args:
        audio_data: Input audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate
        
    Returns:
        Resampled audio data
    """
    if orig_sr == target_sr:
        return audio_data
    
    # Calculate resampling ratio
    ratio = target_sr / orig_sr
    
    # Create new time indices
    orig_length = len(audio_data)
    new_length = int(orig_length * ratio)
    
    # Linear interpolation
    orig_indices = np.linspace(0, orig_length - 1, orig_length)
    new_indices = np.linspace(0, orig_length - 1, new_length)
    
    # Interpolate
    resampled = np.interp(new_indices, orig_indices, audio_data)
    
    return resampled


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


def _load_wav_file(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load WAV file using Python's built-in wave module.
    
    Args:
        file_path: Path to WAV file
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # Get WAV file parameters
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            # Read raw audio data
            raw_audio = wav_file.readframes(n_frames)
            
            # Convert to numpy array based on sample width
            if sample_width == 1:  # 8-bit
                audio_data = np.frombuffer(raw_audio, dtype=np.uint8)
                audio_data = (audio_data.astype(np.float32) - 128) / 128.0
            elif sample_width == 2:  # 16-bit
                audio_data = np.frombuffer(raw_audio, dtype=np.int16)
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif sample_width == 3:  # 24-bit
                # Convert 24-bit to 32-bit integers
                audio_bytes = np.frombuffer(raw_audio, dtype=np.uint8)
                audio_data = []
                for i in range(0, len(audio_bytes), 3):
                    # Convert 3 bytes to 24-bit signed integer
                    sample = int.from_bytes(audio_bytes[i:i+3], 'little', signed=True)
                    audio_data.append(sample)
                audio_data = np.array(audio_data, dtype=np.float32) / 8388608.0
            elif sample_width == 4:  # 32-bit
                audio_data = np.frombuffer(raw_audio, dtype=np.int32)
                audio_data = audio_data.astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width} bytes")
            
            # Convert to mono if stereo
            if n_channels == 2:
                audio_data = audio_data.reshape(-1, 2)
                audio_data = np.mean(audio_data, axis=1)
            elif n_channels > 2:
                audio_data = audio_data.reshape(-1, n_channels)
                audio_data = np.mean(audio_data, axis=1)
            
            return audio_data, sample_rate
            
    except Exception as e:
        raise RuntimeError(f"Failed to load WAV file {file_path}: {e}")


def _save_wav_file(audio_data: np.ndarray, file_path: str, sample_rate: int) -> None:
    """
    Save audio data as WAV file.
    
    Args:
        audio_data: Audio data array
        file_path: Output file path
        sample_rate: Sample rate
    """
    try:
        # Convert to 16-bit integers
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        with wave.open(file_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
            
    except Exception as e:
        raise RuntimeError(f"Failed to save WAV file {file_path}: {e}")