"""
ViSQOL Python wrapper implementation.

This module provides a Python interface to ViSQOL functionality
using the native ViSQOL implementation. Native library build is required.
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
    import soundfile as sf
except ImportError as e:
    raise ImportError(
        "Required audio processing library not found. "
        "Please install with: pip install soundfile"
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
    
    This class provides a Python interface to ViSQOL functionality
    using the native ViSQOL implementation. The native library must
    be built successfully for this package to function.
    """
    
    def __init__(self, mode: ViSQOLMode = ViSQOLMode.AUDIO):
        """
        Initialize ViSQOL instance.
        
        Args:
            mode: Operating mode (AUDIO or SPEECH)
        """
        self.mode = mode
        self._native_available = self._check_native_availability()
        
        if not self._native_available:
            raise ImportError(
                "Native ViSQOL library not found. This package requires the native ViSQOL library to function.\n"
                "Please ensure the package was built with native support:\n"
                "1. Install build dependencies: git, bazel (or let the installer download bazelisk)\n"
                "2. Reinstall: pip uninstall visqol-py && pip install git+https://github.com/diggerdu/visqol-py.git\n"
                "3. Or build manually: python build_native.py\n\n"
                "There is no Python-only fallback because ViSQOL is a complex algorithm\n"
                "that requires the official implementation for meaningful results."
            )
        
        self._init_native()
    
    def _check_native_availability(self) -> bool:
        """Check if native ViSQOL implementation is available."""
        try:
            # Try to import the native ViSQOL library from our built package
            import visqol_py.visqol_lib_py
            import visqol_py.pb2.visqol_config_py_pb2
            import visqol_py.pb2.similarity_result_py_pb2
            return True
        except ImportError:
            try:
                # Fallback to system-wide installation
                from visqol import visqol_lib_py
                from visqol.pb2 import visqol_config_pb2
                return True
            except ImportError:
                return False
    
    def _init_native(self):
        """Initialize native ViSQOL implementation."""
        try:
            # Try to use our built version first
            import visqol_py.visqol_lib_py as visqol_lib_py
            import visqol_py.pb2.visqol_config_py_pb2 as visqol_config_pb2
        except ImportError:
            # Fall back to system installation
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
        # Only native implementation is supported
        return self._measure_native(reference, degraded)
    
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
    
    def _load_audio_native(self, audio: Union[str, np.ndarray, Path]) -> np.ndarray:
        """Load audio for native implementation."""
        if isinstance(audio, np.ndarray):
            return audio.astype(np.float64)
        
        # Load audio file using soundfile
        target_sr = self._config.audio.sample_rate
        audio_data, orig_sr = sf.read(str(audio), always_2d=False)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Resample if needed (using simple linear interpolation)
        if orig_sr != target_sr:
            audio_data = self._resample_audio(audio_data, orig_sr, target_sr)
        
        return audio_data.astype(np.float64)
    
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
                error_msg = f"Failed to process {ref_path} vs {deg_path}: {e}"
                warnings.warn(error_msg)
                # Re-raise the exception - no fake results
                raise RuntimeError(error_msg) from e
        
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
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Simple audio resampling using linear interpolation.
        
        Args:
            audio: Input audio data
            orig_sr: Original sample rate
            target_sr: Target sample rate
            
        Returns:
            Resampled audio data
        """
        if orig_sr == target_sr:
            return audio
        
        # Calculate resampling ratio
        ratio = target_sr / orig_sr
        
        # Create new time indices
        orig_length = len(audio)
        new_length = int(orig_length * ratio)
        
        # Linear interpolation
        orig_indices = np.linspace(0, orig_length - 1, orig_length)
        new_indices = np.linspace(0, orig_length - 1, new_length)
        
        # Interpolate
        resampled = np.interp(new_indices, orig_indices, audio)
        
        return resampled