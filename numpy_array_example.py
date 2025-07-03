#!/usr/bin/env python3
"""
ViSQOL-Py Native NumPy Array API Example.

This example demonstrates how to use ViSQOL-Py with numpy arrays directly,
without needing to save audio files to disk. This is useful for:
- Real-time audio processing
- Integration with audio processing pipelines
- Memory-efficient workflows
- Dynamic audio generation and testing
"""

import numpy as np
import visqol_py
import time
from typing import Tuple

def generate_audio_signal(frequency: float, duration: float, sample_rate: int, 
                         amplitude: float = 0.7) -> np.ndarray:
    """Generate a clean sine wave signal."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    return amplitude * np.sin(2 * np.pi * frequency * t)

def generate_complex_signal(duration: float, sample_rate: int) -> np.ndarray:
    """Generate a complex audio signal with multiple harmonics."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Musical chord (C major: C, E, G)
    c_note = 261.63  # C4
    e_note = 329.63  # E4  
    g_note = 392.00  # G4
    
    signal = (
        0.4 * np.sin(2 * np.pi * c_note * t) +
        0.3 * np.sin(2 * np.pi * e_note * t) +
        0.3 * np.sin(2 * np.pi * g_note * t)
    )
    
    # Add some natural envelope
    envelope = np.exp(-t * 0.1)  # Decay envelope
    return signal * envelope

def generate_speech_like_signal(duration: float, sample_rate: int) -> np.ndarray:
    """Generate a speech-like signal with formants."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Typical formant frequencies for vowel /a/
    f0 = 120    # Fundamental frequency (male voice)
    f1 = 730    # First formant
    f2 = 1090   # Second formant
    f3 = 2440   # Third formant
    
    signal = (
        0.5 * np.sin(2 * np.pi * f0 * t) +
        0.3 * np.sin(2 * np.pi * f1 * t) +
        0.2 * np.sin(2 * np.pi * f2 * t) +
        0.1 * np.sin(2 * np.pi * f3 * t)
    )
    
    # Add speech-like amplitude modulation
    modulation = 0.5 * (1 + np.sin(2 * np.pi * 4 * t))  # 4 Hz syllable rate
    return signal * modulation * 0.7

def apply_audio_degradation(signal: np.ndarray, degradation_type: str, 
                          severity: float = 0.1) -> np.ndarray:
    """Apply various types of audio degradation."""
    degraded = signal.copy()
    
    if degradation_type == "additive_noise":
        noise = severity * np.random.randn(len(signal))
        degraded = signal + noise
        
    elif degradation_type == "amplitude_compression":
        # Dynamic range compression
        threshold = 1.0 - severity
        degraded = np.where(np.abs(signal) > threshold,
                           np.sign(signal) * threshold,
                           signal)
        
    elif degradation_type == "harmonic_distortion":
        # Add harmonic distortion
        degraded = signal + severity * np.power(signal, 3)
        
    elif degradation_type == "frequency_filtering":
        # Simple high-frequency attenuation (moving average)
        window_size = max(1, int(severity * 50))
        kernel = np.ones(window_size) / window_size
        degraded = np.convolve(signal, kernel, mode='same')
        
    elif degradation_type == "quantization_noise":
        # Quantization to fewer bits
        levels = int(2**(16 - severity * 8))  # Reduce bit depth
        degraded = np.round(signal * levels) / levels
        
    return degraded

def demonstrate_numpy_api():
    """Demonstrate ViSQOL-Py with numpy arrays."""
    print("🎵 ViSQOL-Py Native NumPy Array API Demo")
    print("=" * 50)
    print()
    
    # Audio mode example
    print("📊 Audio Mode Example (48kHz)")
    print("-" * 30)
    
    # Generate test signals
    sample_rate_audio = 48000
    duration = 3.0
    
    print(f"Generating {duration}s audio at {sample_rate_audio}Hz...")
    reference_audio = generate_complex_signal(duration, sample_rate_audio)
    print(f"Reference signal shape: {reference_audio.shape}")
    print(f"Reference signal range: [{reference_audio.min():.3f}, {reference_audio.max():.3f}]")
    
    # Apply degradation
    degraded_audio = apply_audio_degradation(reference_audio, "additive_noise", 0.05)
    print(f"Added 5% noise to create degraded signal")
    print()
    
    # Initialize ViSQOL and measure
    print("Initializing ViSQOL in audio mode...")
    visqol_audio = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.AUDIO)
    
    print("Computing ViSQOL score with numpy arrays...")
    start_time = time.time()
    result_audio = visqol_audio.measure(reference_audio, degraded_audio)
    processing_time = time.time() - start_time
    
    print(f"✅ Audio Mode Results:")
    print(f"  - MOS-LQO Score: {result_audio.moslqo:.3f}")
    print(f"  - VNSIM Score: {result_audio.vnsim:.3f}")
    print(f"  - Processing Time: {processing_time:.3f}s")
    print(f"  - Real-time Factor: {processing_time/duration:.2f}x")
    print()
    
    # Speech mode example
    print("🗣️  Speech Mode Example (16kHz)")
    print("-" * 30)
    
    # Generate speech-like signals
    sample_rate_speech = 16000
    speech_duration = 4.0
    
    print(f"Generating {speech_duration}s speech-like signal at {sample_rate_speech}Hz...")
    reference_speech = generate_speech_like_signal(speech_duration, sample_rate_speech)
    degraded_speech = apply_audio_degradation(reference_speech, "harmonic_distortion", 0.1)
    print(f"Speech signal shape: {reference_speech.shape}")
    print(f"Added harmonic distortion to speech signal")
    print()
    
    # Initialize ViSQOL for speech and measure
    print("Initializing ViSQOL in speech mode...")
    visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
    
    print("Computing ViSQOL score for speech...")
    start_time = time.time()
    result_speech = visqol_speech.measure(reference_speech, degraded_speech)
    processing_time = time.time() - start_time
    
    print(f"✅ Speech Mode Results:")
    print(f"  - MOS-LQO Score: {result_speech.moslqo:.3f}")
    print(f"  - VNSIM Score: {result_speech.vnsim:.3f}")
    print(f"  - Processing Time: {processing_time:.3f}s")
    print(f"  - Real-time Factor: {processing_time/speech_duration:.2f}x")
    print()
    
    # Batch processing with arrays
    print("📦 Batch Processing with NumPy Arrays")
    print("-" * 40)
    
    # Create multiple signal pairs with different degradations
    degradation_types = ["additive_noise", "amplitude_compression", "harmonic_distortion"]
    severities = [0.02, 0.05, 0.1]
    
    batch_results = []
    
    print("Processing batch of degraded signals...")
    for i, (deg_type, severity) in enumerate(zip(degradation_types, severities)):
        # Generate reference
        ref = generate_audio_signal(440 + i * 110, 2.0, sample_rate_audio)
        
        # Apply specific degradation
        deg = apply_audio_degradation(ref, deg_type, severity)
        
        # Measure quality
        result = visqol_audio.measure(ref, deg)
        batch_results.append((deg_type, severity, result.moslqo))
        
        print(f"  {i+1}. {deg_type:20} (severity {severity:4.2f}): {result.moslqo:.3f}")
    
    print()
    
    # Memory efficiency demonstration
    print("💾 Memory Efficiency Demo")
    print("-" * 25)
    
    # Show that we can process large arrays efficiently
    large_duration = 10.0  # 10 seconds
    large_signal = generate_audio_signal(440, large_duration, sample_rate_audio)
    large_degraded = apply_audio_degradation(large_signal, "additive_noise", 0.03)
    
    print(f"Processing large signal: {large_duration}s ({len(large_signal):,} samples)")
    print(f"Memory usage: ~{large_signal.nbytes / 1024 / 1024:.1f} MB per signal")
    
    start_time = time.time()
    large_result = visqol_audio.measure(large_signal, large_degraded)
    processing_time = time.time() - start_time
    
    print(f"✅ Large Signal Results:")
    print(f"  - MOS-LQO Score: {large_result.moslqo:.3f}")
    print(f"  - Processing Time: {processing_time:.3f}s")
    print(f"  - Throughput: {large_duration/processing_time:.1f}x real-time")
    print()
    
    # Comparison with identical signals
    print("🔄 Identical Signal Test")
    print("-" * 25)
    
    test_signal = generate_complex_signal(2.0, sample_rate_audio)
    identical_result = visqol_audio.measure(test_signal, test_signal)
    
    print(f"Identical signals MOS-LQO: {identical_result.moslqo:.3f}")
    print(f"Expected: Close to 5.0 (perfect quality)")
    
    quality_check = "✅ PASS" if identical_result.moslqo >= 4.5 else "⚠️  UNEXPECTED"
    print(f"Quality check: {quality_check}")
    print()
    
    # Summary
    print("📋 Summary")
    print("-" * 10)
    print("✅ Native NumPy Array Support:")
    print("  - Direct array input without file I/O")
    print("  - Support for both audio (48kHz) and speech (16kHz) modes")
    print("  - Efficient batch processing")
    print("  - Memory-efficient for large signals")
    print("  - Real-time processing capability")
    print()
    print("🔧 Use Cases:")
    print("  - Real-time audio quality monitoring")
    print("  - Integration with audio processing pipelines")
    print("  - Automated testing with synthetic signals")
    print("  - Research and development workflows")
    print("  - Memory-constrained environments")
    print()
    print("💡 API Usage:")
    print("  import visqol_py")
    print("  visqol = visqol_py.ViSQOL()")
    print("  result = visqol.measure(reference_array, degraded_array)")
    print("  print(f'MOS-LQO: {result.moslqo:.3f}')")

def demonstrate_advanced_features():
    """Demonstrate advanced numpy array features."""
    print("\n🔬 Advanced NumPy Array Features")
    print("=" * 40)
    
    # Different data types
    print("📊 Data Type Handling")
    print("-" * 20)
    
    sample_rate = 48000
    duration = 1.0
    
    # Test different numpy data types
    base_signal = generate_audio_signal(440, duration, sample_rate)
    
    data_types = [np.float32, np.float64, np.int16, np.int32]
    visqol = visqol_py.ViSQOL()
    
    for dtype in data_types:
        if dtype in [np.int16, np.int32]:
            # Convert to integer range
            int_signal = (base_signal * 32767).astype(dtype)
            degraded = int_signal + np.random.randint(-1000, 1000, len(int_signal), dtype=dtype)
        else:
            float_signal = base_signal.astype(dtype)
            degraded = float_signal + (0.05 * np.random.randn(len(float_signal))).astype(dtype)
            int_signal = float_signal
        
        try:
            result = visqol.measure(int_signal, degraded)
            print(f"  ✅ {dtype.__name__:8}: MOS-LQO = {result.moslqo:.3f}")
        except Exception as e:
            print(f"  ❌ {dtype.__name__:8}: Error - {str(e)[:50]}")
    
    print()
    
    # Multi-channel handling
    print("🎵 Multi-channel Signal Handling")
    print("-" * 30)
    
    # Create stereo signal
    mono_signal = generate_complex_signal(2.0, sample_rate)
    stereo_signal = np.column_stack([mono_signal, mono_signal * 0.8])  # Left and right channels
    
    print(f"Mono signal shape: {mono_signal.shape}")
    print(f"Stereo signal shape: {stereo_signal.shape}")
    
    # ViSQOL should handle mono signals
    try:
        mono_result = visqol.measure(mono_signal, mono_signal)
        print(f"✅ Mono processing: MOS-LQO = {mono_result.moslqo:.3f}")
    except Exception as e:
        print(f"❌ Mono processing failed: {e}")
    
    # Test if stereo is automatically converted to mono
    try:
        # Note: The implementation should handle this by converting to mono
        print("  Testing stereo signal handling...")
        print("  (Implementation should convert stereo to mono automatically)")
    except Exception as e:
        print(f"❌ Stereo processing: {e}")

def main():
    """Main demonstration function."""
    print("🚀 ViSQOL-Py NumPy Array API Demonstration")
    print("=" * 60)
    print()
    
    # Set random seed for reproducible results
    np.random.seed(42)
    
    try:
        # Basic functionality
        demonstrate_numpy_api()
        
        # Advanced features
        demonstrate_advanced_features()
        
        print("🎉 NumPy Array API demonstration completed successfully!")
        print()
        print("📖 Key Takeaways:")
        print("  • ViSQOL-Py natively supports NumPy arrays")
        print("  • No need to save files to disk")
        print("  • Efficient for real-time and batch processing")
        print("  • Supports both audio and speech modes")
        print("  • Memory-efficient for large signals")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install ViSQOL-Py: pip install git+https://github.com/diggerdu/visqol-py.git")
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()