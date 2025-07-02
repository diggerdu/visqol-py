"""Tests for ViSQOL-Py wrapper."""

import pytest
import numpy as np
import tempfile
from pathlib import Path

from visqol_py import ViSQOL, ViSQOLMode, ViSQOLResult


class TestViSQOL:
    """Test cases for ViSQOL class."""
    
    def test_init_audio_mode(self):
        """Test initialization in audio mode."""
        visqol = ViSQOL(mode=ViSQOLMode.AUDIO)
        assert visqol.mode == ViSQOLMode.AUDIO
    
    def test_init_speech_mode(self):
        """Test initialization in speech mode."""
        visqol = ViSQOL(mode=ViSQOLMode.SPEECH)
        assert visqol.mode == ViSQOLMode.SPEECH
    
    def test_measure_with_arrays(self):
        """Test measure method with numpy arrays."""
        visqol = ViSQOL()
        
        # Create test signals
        sample_rate = 48000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        reference = np.sin(2 * np.pi * 440 * t)
        degraded = reference + 0.1 * np.random.randn(len(reference))
        
        result = visqol.measure(reference, degraded)
        
        assert isinstance(result, ViSQOLResult)
        assert 1.0 <= result.moslqo <= 5.0
    
    def test_measure_identical_signals(self):
        """Test measure with identical signals."""
        visqol = ViSQOL()
        
        # Create identical signals
        sample_rate = 48000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 440 * t)
        
        result = visqol.measure(signal, signal)
        
        # Identical signals should have high quality scores
        assert result.moslqo >= 4.0
    
    def test_measure_with_files(self):
        """Test measure method with audio files."""
        visqol = ViSQOL()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary audio files
            ref_path = Path(temp_dir) / "ref.wav"
            deg_path = Path(temp_dir) / "deg.wav"
            
            # Generate test audio
            sample_rate = 48000
            duration = 2.0
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            reference = np.sin(2 * np.pi * 440 * t)
            degraded = reference + 0.05 * np.random.randn(len(reference))
            
            # Save as WAV files
            import soundfile as sf
            sf.write(ref_path, reference, sample_rate)
            sf.write(deg_path, degraded, sample_rate)
            
            # Test measure
            result = visqol.measure(ref_path, deg_path)
            
            assert isinstance(result, ViSQOLResult)
            assert 1.0 <= result.moslqo <= 5.0
            assert result.reference_path == str(ref_path)
            assert result.degraded_path == str(deg_path)
    
    def test_measure_batch(self):
        """Test batch processing."""
        visqol = ViSQOL()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file pairs
            file_pairs = []
            for i in range(3):
                ref_path = temp_path / f"ref_{i}.wav"
                deg_path = temp_path / f"deg_{i}.wav"
                
                # Generate different test signals
                sample_rate = 48000
                duration = 1.0
                t = np.linspace(0, duration, int(sample_rate * duration))
                
                reference = np.sin(2 * np.pi * (440 + i * 110) * t)
                degraded = reference + (0.05 * i) * np.random.randn(len(reference))
                
                import soundfile as sf
                sf.write(ref_path, reference, sample_rate)
                sf.write(deg_path, degraded, sample_rate)
                
                file_pairs.append((str(ref_path), str(deg_path)))
            
            # Test batch processing
            results = visqol.measure_batch(file_pairs)
            
            assert len(results) == 3
            for result in results:
                assert isinstance(result, ViSQOLResult)
                assert 1.0 <= result.moslqo <= 5.0
    
    def test_speech_mode(self):
        """Test speech mode functionality."""
        visqol = ViSQOL(mode=ViSQOLMode.SPEECH)
        
        # Create speech-like signal at 16kHz
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Speech-like signal with harmonics
        reference = (
            0.5 * np.sin(2 * np.pi * 200 * t) +
            0.3 * np.sin(2 * np.pi * 400 * t)
        )
        degraded = reference + 0.05 * np.random.randn(len(reference))
        
        result = visqol.measure(reference, degraded)
        
        assert isinstance(result, ViSQOLResult)
        assert 1.0 <= result.moslqo <= 5.0


class TestViSQOLResult:
    """Test cases for ViSQOLResult class."""
    
    def test_result_creation(self):
        """Test ViSQOLResult creation."""
        result = ViSQOLResult(moslqo=3.5, vnsim=0.8)
        
        assert result.moslqo == 3.5
        assert result.vnsim == 0.8
        assert result.fvnsim == []
        assert result.center_freq_bands == []
    
    def test_result_str(self):
        """Test string representation."""
        result = ViSQOLResult(moslqo=3.5, vnsim=0.8)
        str_repr = str(result)
        
        assert "3.500" in str_repr
        assert "0.800" in str_repr


class TestViSQOLModes:
    """Test cases for ViSQOL modes."""
    
    def test_mode_enum_values(self):
        """Test mode enum values."""
        assert ViSQOLMode.AUDIO.value == "audio"
        assert ViSQOLMode.SPEECH.value == "speech"
    
    def test_mode_comparison(self):
        """Test comparing results from different modes."""
        # Create test signal suitable for both modes
        sample_rate_audio = 48000
        sample_rate_speech = 16000
        duration = 2.0
        
        # Audio mode signal
        t_audio = np.linspace(0, duration, int(sample_rate_audio * duration))
        ref_audio = np.sin(2 * np.pi * 440 * t_audio)
        deg_audio = ref_audio + 0.05 * np.random.randn(len(ref_audio))
        
        # Speech mode signal (downsampled)
        from scipy import signal
        ref_speech = signal.resample(ref_audio, int(sample_rate_speech * duration))
        deg_speech = signal.resample(deg_audio, int(sample_rate_speech * duration))
        
        # Test both modes
        visqol_audio = ViSQOL(mode=ViSQOLMode.AUDIO)
        visqol_speech = ViSQOL(mode=ViSQOLMode.SPEECH)
        
        result_audio = visqol_audio.measure(ref_audio, deg_audio)
        result_speech = visqol_speech.measure(ref_speech, deg_speech)
        
        # Both should produce valid scores
        assert 1.0 <= result_audio.moslqo <= 5.0
        assert 1.0 <= result_speech.moslqo <= 5.0


class TestViSQOLFallback:
    """Test fallback implementation."""
    
    def test_fallback_similarity_computation(self):
        """Test fallback similarity computation."""
        visqol = ViSQOL()
        
        # Test the fallback similarity method directly
        sample_rate = 48000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        reference = np.sin(2 * np.pi * 440 * t)
        degraded = reference + 0.1 * np.random.randn(len(reference))
        
        # This should work even without native ViSQOL
        score = visqol._compute_fallback_similarity(reference, degraded)
        
        assert 1.0 <= score <= 5.0
    
    def test_fallback_with_different_lengths(self):
        """Test fallback with different signal lengths."""
        visqol = ViSQOL()
        
        # Create signals of different lengths
        sample_rate = 48000
        t1 = np.linspace(0, 1.0, sample_rate)
        t2 = np.linspace(0, 2.0, 2 * sample_rate)
        
        reference = np.sin(2 * np.pi * 440 * t1)
        degraded = np.sin(2 * np.pi * 440 * t2) + 0.1 * np.random.randn(2 * sample_rate)
        
        # Fallback should handle different lengths
        score = visqol._compute_fallback_similarity(reference, degraded)
        
        assert 1.0 <= score <= 5.0


if __name__ == "__main__":
    pytest.main([__file__])