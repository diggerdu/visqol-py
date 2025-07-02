"""
ViSQOL Python wrapper implementation.

This module provides a simplified Python interface to ViSQOL functionality
without requiring Bazel installation.
"""

import os
import sys
import warnings
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from pathlib import Path

import numpy as np

try:
    import librosa
    import soundfile as sf
except ImportError as e:
    raise ImportError(
        "Required audio processing libraries not found. "
        "Please install with: pip install librosa soundfile"
    ) from e


class ViSQOLMode(Enum):
    """ViSQOL operating modes."""
    AUDIO = "audio"  # 48kHz, full-band audio
    SPEECH = "speech"  # 16kHz, speech with VAD


@dataclass
class ViSQOLResult:
    """ViSQOL computation results."""
    moslqo: float
    vnsim: float = 0.0
    fvnsim: List[float] = field(default_factory=list)
    center_freq_bands: List[float] = field(default_factory=list)
    patch_similarities: List[Dict[str, Any]] = field(default_factory=list)
    reference_path: Optional[str] = None
    degraded_path: Optional[str] = None
    
    def __str__(self) -> str:
        return f"ViSQOLResult(MOS-LQO: {self.moslqo:.3f}, VNSIM: {self.vnsim:.3f})"


class ViSQOL:
    """
    ViSQOL Python wrapper class.
    
    This class provides a simplified interface to ViSQOL functionality.
    For full compatibility with the original ViSQOL, it attempts to use
    the native implementation if available, otherwise falls back to 
    approximation methods.
    """
    
    def __init__(self, mode: ViSQOLMode = ViSQOLMode.AUDIO):
        """
        Initialize ViSQOL instance.
        
        Args:
            mode: Operating mode (AUDIO or SPEECH)
        """
        self.mode = mode
        self._native_available = self._check_native_availability()
        
        if self._native_available:
            self._init_native()
        else:
            self._init_fallback()
            warnings.warn(
                "Native ViSQOL not available. Using fallback implementation. "
                "Results may differ from official ViSQOL implementation.",
                UserWarning
            )
    
    def _check_native_availability(self) -> bool:
        """Check if native ViSQOL implementation is available."""
        try:
            # Try to import the native ViSQOL library
            from visqol import visqol_lib_py
            from visqol.pb2 import visqol_config_pb2
            return True
        except ImportError:
            return False
    
    def _init_native(self):
        """Initialize native ViSQOL implementation."""
        from visqol import visqol_lib_py
        from visqol.pb2 import visqol_config_pb2
        
        self._config = visqol_config_pb2.VisqolConfig()
        
        if self.mode == ViSQOLMode.AUDIO:
            self._config.audio.sample_rate = 48000
            self._config.options.use_speech_scoring = False
            model_file = "libsvm_nu_svr_model.txt"
        else:  # SPEECH mode
            self._config.audio.sample_rate = 16000
            self._config.options.use_speech_scoring = True
            model_file = "lattice_tcditugenmeetpackhref_ls2_nl60_lr12_bs2048_learn.005_ep2400_train1_7_raw.tflite"
        
        # Set model path
        model_path = os.path.join(
            os.path.dirname(visqol_lib_py.__file__), "model", model_file
        )
        self._config.options.svr_model_path = model_path
        
        # Create API instance
        self._api = visqol_lib_py.VisqolApi()
        self._api.Create(self._config)
    
    def _init_fallback(self):
        """Initialize fallback implementation."""
        self.sample_rate = 48000 if self.mode == ViSQOLMode.AUDIO else 16000
        
        # Placeholder for fallback implementation
        # In a real implementation, you might:
        # 1. Implement a simplified spectral similarity metric
        # 2. Use pre-trained models (sklearn, tensorflow, etc.)
        # 3. Provide approximation using other audio quality metrics
    
    def measure(
        self,
        reference: Union[str, np.ndarray, Path],
        degraded: Union[str, np.ndarray, Path]
    ) -> ViSQOLResult:
        """
        Compute ViSQOL score between reference and degraded audio.
        
        Args:
            reference: Reference audio (file path or numpy array)
            degraded: Degraded audio (file path or numpy array)
            
        Returns:
            ViSQOLResult containing MOS-LQO score and additional metrics
        """
        if self._native_available:
            return self._measure_native(reference, degraded)
        else:
            return self._measure_fallback(reference, degraded)
    
    def _measure_native(
        self,
        reference: Union[str, np.ndarray, Path],
        degraded: Union[str, np.ndarray, Path]
    ) -> ViSQOLResult:
        """Measure using native ViSQOL implementation."""
        # Load audio if needed
        ref_audio = self._load_audio_native(reference)
        deg_audio = self._load_audio_native(degraded)
        
        # Run ViSQOL
        similarity_result = self._api.Measure(ref_audio, deg_audio)
        
        # Convert to our result format
        return ViSQOLResult(
            moslqo=similarity_result.moslqo,
            vnsim=similarity_result.vnsim,
            fvnsim=list(similarity_result.fvnsim),
            center_freq_bands=list(similarity_result.center_freq_bands),
            reference_path=str(reference) if isinstance(reference, (str, Path)) else None,
            degraded_path=str(degraded) if isinstance(degraded, (str, Path)) else None,
        )
    
    def _measure_fallback(
        self,
        reference: Union[str, np.ndarray, Path],
        degraded: Union[str, np.ndarray, Path]
    ) -> ViSQOLResult:
        """Measure using fallback implementation."""
        # Load audio
        ref_audio, sr_ref = self._load_audio_fallback(reference)
        deg_audio, sr_deg = self._load_audio_fallback(degraded)
        
        # Ensure same sample rate
        if sr_ref != sr_deg:
            warnings.warn(f"Sample rate mismatch: {sr_ref} vs {sr_deg}. Resampling degraded.")
            deg_audio = librosa.resample(deg_audio, orig_sr=sr_deg, target_sr=sr_ref)
        
        # Resample to target sample rate if needed
        if sr_ref != self.sample_rate:
            ref_audio = librosa.resample(ref_audio, orig_sr=sr_ref, target_sr=self.sample_rate)
            deg_audio = librosa.resample(deg_audio, orig_sr=sr_deg, target_sr=self.sample_rate)
        
        # Compute fallback similarity metric
        moslqo = self._compute_fallback_similarity(ref_audio, deg_audio)
        
        return ViSQOLResult(
            moslqo=moslqo,
            reference_path=str(reference) if isinstance(reference, (str, Path)) else None,
            degraded_path=str(degraded) if isinstance(degraded, (str, Path)) else None,
        )
    
    def _load_audio_native(self, audio: Union[str, np.ndarray, Path]) -> np.ndarray:
        """Load audio for native implementation."""
        if isinstance(audio, np.ndarray):
            return audio.astype(np.float64)
        
        # For native implementation, we need to load with the exact sample rate
        audio_data, sr = librosa.load(str(audio), sr=self.sample_rate, mono=True)
        return audio_data.astype(np.float64)
    
    def _load_audio_fallback(self, audio: Union[str, np.ndarray, Path]) -> tuple:
        """Load audio for fallback implementation."""
        if isinstance(audio, np.ndarray):
            return audio, self.sample_rate
        
        # Load audio with original sample rate
        audio_data, sr = librosa.load(str(audio), sr=None, mono=True)
        return audio_data, sr
    
    def _compute_fallback_similarity(self, reference: np.ndarray, degraded: np.ndarray) -> float:
        """
        Compute a fallback similarity metric.
        
        This is a simplified implementation that provides a rough approximation
        of audio quality. For production use, consider using the full ViSQOL
        implementation or other established metrics.
        """
        # Ensure same length
        min_len = min(len(reference), len(degraded))
        ref = reference[:min_len]
        deg = degraded[:min_len]
        
        # Compute spectral features
        ref_spec = np.abs(librosa.stft(ref, hop_length=512, n_fft=2048))
        deg_spec = np.abs(librosa.stft(deg, hop_length=512, n_fft=2048))
        
        # Compute spectral correlation
        correlation = np.corrcoef(ref_spec.flatten(), deg_spec.flatten())[0, 1]
        
        # Convert to MOS-like scale (1-5)
        # This is a very rough approximation
        if np.isnan(correlation):
            correlation = 0.0
        
        # Map correlation [-1, 1] to MOS [1, 5]
        mos_score = 1.0 + 4.0 * max(0.0, correlation)
        
        # Add some spectral distance penalty
        spectral_distance = np.mean(np.abs(ref_spec - deg_spec))
        spectral_penalty = min(1.0, spectral_distance / np.mean(ref_spec))
        
        final_score = mos_score * (1.0 - 0.5 * spectral_penalty)
        
        return max(1.0, min(5.0, final_score))
    
    def measure_batch(
        self,
        file_pairs: List[tuple],
        output_csv: Optional[str] = None
    ) -> List[ViSQOLResult]:
        """
        Measure ViSQOL scores for multiple file pairs.
        
        Args:
            file_pairs: List of (reference_path, degraded_path) tuples
            output_csv: Optional path to save results as CSV
            
        Returns:
            List of ViSQOLResult objects
        """
        results = []
        
        for ref_path, deg_path in file_pairs:
            try:
                result = self.measure(ref_path, deg_path)
                results.append(result)
            except Exception as e:
                warnings.warn(f"Failed to process {ref_path} vs {deg_path}: {e}")
                # Add placeholder result
                results.append(ViSQOLResult(
                    moslqo=1.0,
                    reference_path=str(ref_path),
                    degraded_path=str(deg_path)
                ))
        
        # Save to CSV if requested
        if output_csv:
            self._save_batch_results(results, output_csv)
        
        return results
    
    def _save_batch_results(self, results: List[ViSQOLResult], output_path: str):
        """Save batch results to CSV file."""
        import csv
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['reference', 'degraded', 'moslqo'])
            
            for result in results:
                writer.writerow([
                    result.reference_path or '',
                    result.degraded_path or '',
                    f"{result.moslqo:.6f}"
                ])