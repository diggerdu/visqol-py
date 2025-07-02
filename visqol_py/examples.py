"""
Example usage of ViSQOL-Py.

This module contains various examples showing how to use the ViSQOL-Py wrapper.
"""

import numpy as np
import tempfile
import os
from pathlib import Path

# Import the ViSQOL wrapper
try:
    from . import ViSQOL, ViSQOLMode, load_audio, save_results
except ImportError:
    # For standalone execution
    from visqol_py import ViSQOL, ViSQOLMode, load_audio, save_results


def example_basic_usage():
    """Basic example of computing ViSQOL scores."""
    print("=== Basic Usage Example ===")
    
    # Create some test audio (sine waves)
    sample_rate = 48000
    duration = 5.0  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Reference: clean sine wave
    reference = np.sin(2 * np.pi * 440 * t)  # A4 note
    
    # Degraded: same sine wave with added noise
    noise_level = 0.1
    degraded = reference + noise_level * np.random.randn(len(reference))
    
    # Initialize ViSQOL in audio mode (48kHz)
    visqol = ViSQOL(mode=ViSQOLMode.AUDIO)
    
    # Compute the score
    result = visqol.measure(reference, degraded)
    
    print(f"MOS-LQO Score: {result.moslqo:.3f}")
    print(f"VNSIM Score: {result.vnsim:.3f}")
    print()


def example_speech_mode():
    """Example using speech mode."""
    print("=== Speech Mode Example ===")
    
    # Create test speech-like signal (16kHz)
    sample_rate = 16000
    duration = 8.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Speech-like signal: mix of frequencies with amplitude modulation
    reference = (
        0.5 * np.sin(2 * np.pi * 200 * t) +  # Fundamental
        0.3 * np.sin(2 * np.pi * 400 * t) +  # First harmonic
        0.2 * np.sin(2 * np.pi * 600 * t)    # Second harmonic
    )
    
    # Add amplitude modulation to simulate speech patterns
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 3 * t))
    reference *= envelope
    
    # Degraded version with compression artifacts
    degraded = np.tanh(2 * reference) / 2  # Soft clipping
    
    # Initialize ViSQOL in speech mode
    visqol = ViSQOL(mode=ViSQOLMode.SPEECH)
    
    # Compute the score
    result = visqol.measure(reference, degraded)
    
    print(f"Speech MOS-LQO Score: {result.moslqo:.3f}")
    print()


def example_file_processing():
    """Example processing actual audio files."""
    print("=== File Processing Example ===")
    
    # This example assumes you have audio files
    # For demonstration, we'll create temporary files
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create temporary audio files
        ref_path = Path(temp_dir) / "reference.wav"
        deg_path = Path(temp_dir) / "degraded.wav"
        
        # Generate test audio
        sample_rate = 48000
        duration = 6.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Reference: clean signal
        reference = np.sin(2 * np.pi * 440 * t) * 0.7
        
        # Degraded: add distortion
        degraded = np.tanh(reference * 1.5) * 0.7
        
        # Save as WAV files
        import soundfile as sf
        sf.write(ref_path, reference, sample_rate)
        sf.write(deg_path, degraded, sample_rate)
        
        # Process with ViSQOL
        visqol = ViSQOL()
        result = visqol.measure(ref_path, deg_path)
        
        print(f"File-based MOS-LQO: {result.moslqo:.3f}")
        print(f"Reference: {result.reference_path}")
        print(f"Degraded: {result.degraded_path}")
        print()


def example_batch_processing():
    """Example of batch processing multiple file pairs."""
    print("=== Batch Processing Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create multiple test file pairs
        sample_rate = 48000
        duration = 4.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        file_pairs = []
        
        for i in range(3):
            # Different degradation levels
            noise_level = 0.05 * (i + 1)  # Increasing noise
            
            ref_path = temp_path / f"ref_{i+1}.wav"
            deg_path = temp_path / f"deg_{i+1}.wav"
            
            # Reference
            reference = np.sin(2 * np.pi * (440 + i * 110) * t) * 0.7
            
            # Degraded with different noise levels
            degraded = reference + noise_level * np.random.randn(len(reference))
            
            # Save files
            import soundfile as sf
            sf.write(ref_path, reference, sample_rate)
            sf.write(deg_path, degraded, sample_rate)
            
            file_pairs.append((str(ref_path), str(deg_path)))
        
        # Process batch
        visqol = ViSQOL()
        results = visqol.measure_batch(file_pairs)
        
        # Display results
        print("Batch Results:")
        for i, result in enumerate(results, 1):
            print(f"  Pair {i}: MOS-LQO = {result.moslqo:.3f}")
        
        # Save results to CSV
        results_csv = temp_path / "batch_results.csv"
        save_results(results, results_csv)
        print(f"Results saved to: {results_csv}")
        
        # Show CSV content
        with open(results_csv, 'r') as f:
            print("CSV Content:")
            print(f.read())


def example_parameter_exploration():
    """Example exploring different parameters and their effects."""
    print("=== Parameter Exploration Example ===")
    
    sample_rate = 48000
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create reference signal
    reference = np.sin(2 * np.pi * 440 * t) * 0.7
    
    # Test different degradation types
    degradations = {
        "Low Noise": reference + 0.02 * np.random.randn(len(reference)),
        "High Noise": reference + 0.15 * np.random.randn(len(reference)),
        "Clipping": np.clip(reference * 2, -0.8, 0.8),
        "Low-pass": None,  # Will be created using scipy
    }
    
    # Create low-pass filtered version
    try:
        from scipy import signal
        b, a = signal.butter(5, 8000, fs=sample_rate, btype='low')
        degradations["Low-pass"] = signal.filtfilt(b, a, reference)
    except ImportError:
        print("Scipy not available, skipping low-pass filter example")
        del degradations["Low-pass"]
    
    # Initialize ViSQOL
    visqol = ViSQOL()
    
    print("Degradation Type vs MOS-LQO Score:")
    for deg_type, degraded in degradations.items():
        if degraded is not None:
            result = visqol.measure(reference, degraded)
            print(f"  {deg_type:12}: {result.moslqo:.3f}")
    print()


def example_comparing_modes():
    """Example comparing audio vs speech modes."""
    print("=== Mode Comparison Example ===")
    
    # Create a signal that works for both modes
    # We'll generate at 48kHz and downsample for speech mode
    
    sample_rate_high = 48000
    sample_rate_speech = 16000
    duration = 6.0
    
    # Create reference signal at 48kHz
    t_high = np.linspace(0, duration, int(sample_rate_high * duration))
    reference_48k = np.sin(2 * np.pi * 440 * t_high) * 0.7
    degraded_48k = reference_48k + 0.05 * np.random.randn(len(reference_48k))
    
    # Downsample for speech mode
    from scipy import signal as scipy_signal
    reference_16k = scipy_signal.resample(reference_48k, int(sample_rate_speech * duration))
    degraded_16k = scipy_signal.resample(degraded_48k, int(sample_rate_speech * duration))
    
    # Test both modes
    visqol_audio = ViSQOL(mode=ViSQOLMode.AUDIO)
    visqol_speech = ViSQOL(mode=ViSQOLMode.SPEECH)
    
    result_audio = visqol_audio.measure(reference_48k, degraded_48k)
    result_speech = visqol_speech.measure(reference_16k, degraded_16k)
    
    print(f"Audio Mode (48kHz):  MOS-LQO = {result_audio.moslqo:.3f}")
    print(f"Speech Mode (16kHz): MOS-LQO = {result_speech.moslqo:.3f}")
    print()


def run_all_examples():
    """Run all examples."""
    print("ViSQOL-Py Examples\n" + "=" * 50)
    
    example_basic_usage()
    example_speech_mode()
    example_file_processing()
    example_batch_processing()
    example_parameter_exploration()
    
    try:
        example_comparing_modes()
    except ImportError:
        print("Skipping mode comparison example (scipy not available)")


if __name__ == "__main__":
    run_all_examples()