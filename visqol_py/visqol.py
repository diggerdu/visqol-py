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
from typing import List, Optional, Union, Dict, Any, Tuple
from pathlib import Path

import numpy as np

import struct
import wave


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
            self._config.audio.sample_rate = 48000  # Default, will be updated per audio file
            self._config.options.use_speech_scoring = False
            self._config.options.use_lattice_model = False  # Not yet supported for audio mode
            self._config.options.search_window_radius = 60  # Default search window
            model_file = "libsvm_nu_svr_model.txt"
        else:  # SPEECH mode
            self._config.audio.sample_rate = 16000  # Default, will be updated based on input
            self._config.options.use_speech_scoring = True
            self._config.options.use_lattice_model = True  # Use lattice model by default
            self._config.options.detect_voice_activity = True  # Enable VAD for speech
            self._config.options.use_unscaled_speech_mos_mapping = False  # Use scaled mapping (perfect NSIM -> MOS 5.0)
            self._config.options.search_window_radius = 60  # Default search window radius
            model_file = "lattice_tcditugenmeetpackhref_ls2_nl60_lr12_bs2048_learn.005_ep2400_train1_7_raw.tflite"
        
        # Set model path
        self._model_path = os.path.join(
            os.path.dirname(visqol_lib_py.__file__), "model", model_file
        )
        self._config.options.svr_model_path = self._model_path
        
        # Store libs for later use
        self._visqol_lib_py = visqol_lib_py
        
        # Create API instance with default config
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
        # Load audio and determine actual sample rate
        ref_audio, actual_sr = self._load_audio_with_sr(reference)
        deg_audio, _ = self._load_audio_with_sr(degraded)
        
        # Create API with correct sample rate if different from default
        api_to_use = self._get_api_for_sample_rate(actual_sr)
        
        # Run ViSQOL
        similarity_result = api_to_use.Measure(ref_audio, deg_audio)
        
        # Convert to our result format
        return ViSQOLResult(
            moslqo=similarity_result.moslqo,
            vnsim=similarity_result.vnsim,
            fvnsim=list(similarity_result.fvnsim),
            center_freq_bands=list(similarity_result.center_freq_bands),
            reference_path=str(reference) if isinstance(reference, (str, Path)) else None,
            degraded_path=str(degraded) if isinstance(degraded, (str, Path)) else None,
        )
    
    def _get_api_for_sample_rate(self, sample_rate: int):
        """Get or create API instance for specific sample rate."""
        # If sample rate matches current config, use existing API
        if sample_rate == self._config.audio.sample_rate:
            return self._api
        
        # Create new API with correct sample rate
        import visqol_py.pb2.visqol_config_py_pb2 as visqol_config_pb2
        
        config = visqol_config_pb2.VisqolConfig()
        config.audio.sample_rate = sample_rate
        
        # Copy all options from original config
        config.options.use_speech_scoring = self._config.options.use_speech_scoring
        config.options.use_lattice_model = self._config.options.use_lattice_model
        config.options.detect_voice_activity = self._config.options.detect_voice_activity
        config.options.use_unscaled_speech_mos_mapping = self._config.options.use_unscaled_speech_mos_mapping
        config.options.search_window_radius = self._config.options.search_window_radius
        config.options.svr_model_path = self._model_path
        
        # Create new API instance
        api = self._visqol_lib_py.VisqolApi()
        api.Create(config)
        return api
    
    def _load_audio_with_sr(self, audio: Union[str, np.ndarray, Path]) -> Tuple[np.ndarray, int]:
        """Load audio and return both data and actual sample rate used."""
        if isinstance(audio, np.ndarray):
            # For numpy arrays, assume they match the default config sample rate
            default_sr = 16000 if self.mode == ViSQOLMode.SPEECH else 48000
            return audio.astype(np.float64), default_sr
        
        # Load WAV file
        audio_data, orig_sr = self._load_wav_file(str(audio))
        
        # Determine target sample rate
        target_sr = self._get_target_sample_rate(orig_sr)
        
        # Resample if needed
        if orig_sr != target_sr:
            audio_data = self._resample_audio(audio_data, orig_sr, target_sr)
        
        return audio_data.astype(np.float64), target_sr
    
    
    def _get_target_sample_rate(self, original_sr: int) -> int:
        """
        Determine target sample rate based on mode and original sample rate.
        
        This matches original ViSQOL behavior:
        - Speech mode: Use original SR if >= 16kHz, otherwise upsample to 16kHz
        - Audio mode: Always use 48kHz
        """
        if self.mode == ViSQOLMode.SPEECH:
            # In speech mode, if original is already >= 16kHz, keep it
            # This matches how original ViSQOL handles 48kHz files in speech mode
            if original_sr >= 16000:
                return original_sr
            else:
                return 16000
        else:  # AUDIO mode
            return 48000
    
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
    
    def _load_wav_file(self, file_path: str) -> Tuple[np.ndarray, int]:
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
    
    def _save_wav_file(self, audio_data: np.ndarray, file_path: str, sample_rate: int) -> None:
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