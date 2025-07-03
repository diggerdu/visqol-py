#!/usr/bin/env python3
"""
Simple usage example for ViSQOL-Py package.

This script demonstrates basic usage of the ViSQOL-Py API with
randomly generated audio samples.
"""

import numpy as np
import visqol_py

def main():
    print("🎵 ViSQOL-Py Usage Example")
    print("=" * 40)
    
    # Create test audio signals
    print("Generating test audio signals...")
    
    sample_rate = 48000
    duration = 3.0  # 3 seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Reference: Clean sine wave
    reference = np.sin(2 * np.pi * 440 * t) * 0.7  # A4 note
    
    # Degraded: Add some noise
    noise_level = 0.05
    degraded = reference + noise_level * np.random.randn(len(reference))
    
    print(f"  - Reference: {len(reference)} samples at {sample_rate}Hz")
    print(f"  - Degraded: Added {noise_level} noise level")
    print()
    
    # Initialize ViSQOL in audio mode
    print("Initializing ViSQOL (Audio Mode)...")
    visqol = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.AUDIO)
    print(f"  - Mode: {visqol.mode.value}")
    print()
    
    # Compute ViSQOL score
    print("Computing ViSQOL score...")
    result = visqol.measure(reference, degraded)
    
    # Display results
    print("Results:")
    print(f"  - MOS-LQO Score: {result.moslqo:.3f}")
    print(f"  - VNSIM Score: {result.vnsim:.3f}")
    print()
    
    # Test speech mode
    print("Testing Speech Mode...")
    
    # Create speech-like signal at 16kHz
    speech_sample_rate = 16000
    speech_duration = 4.0
    t_speech = np.linspace(0, speech_duration, int(speech_sample_rate * speech_duration))
    
    # Speech-like signal with formants
    fundamental = 120  # Typical male voice fundamental
    speech_ref = (
        0.4 * np.sin(2 * np.pi * fundamental * t_speech) +
        0.3 * np.sin(2 * np.pi * fundamental * 2 * t_speech) +
        0.2 * np.sin(2 * np.pi * fundamental * 3 * t_speech)
    )
    
    # Add speech-like modulation
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 3 * t_speech))
    speech_ref *= envelope
    
    # Degraded speech
    speech_deg = speech_ref + 0.03 * np.random.randn(len(speech_ref))
    
    # Initialize ViSQOL in speech mode
    visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
    speech_result = visqol_speech.measure(speech_ref, speech_deg)
    
    print(f"  - Speech MOS-LQO: {speech_result.moslqo:.3f}")
    print()
    
    # Test different degradation levels
    print("Testing different degradation levels...")
    
    degradation_levels = [0.0, 0.02, 0.05, 0.1, 0.2]
    scores = []
    
    for noise in degradation_levels:
        if noise == 0.0:
            test_degraded = reference  # No degradation
        else:
            test_degraded = reference + noise * np.random.randn(len(reference))
        
        test_result = visqol.measure(reference, test_degraded)
        scores.append(test_result.moslqo)
        print(f"  - Noise level {noise:4.2f}: MOS-LQO = {test_result.moslqo:.3f}")
    
    print()
    print("Score trend (should generally decrease with more degradation):")
    print(f"  Scores: {' → '.join([f'{s:.3f}' for s in scores])}")
    
    # Check if trend is correct
    trend_correct = all(scores[i] >= scores[i+1] - 0.5 for i in range(len(scores)-1))
    trend_status = "✅" if trend_correct else "⚠️"
    print(f"  Trend: {trend_status} {'Correct' if trend_correct else 'Irregular'}")
    print()
    
    print("✨ Example completed successfully!")
    print()
    print("Try this yourself:")
    print("  python example_usage.py")
    print()
    print("For more examples, see:")
    print("  python -c 'from visqol_py.examples import run_all_examples; run_all_examples()'")

if __name__ == "__main__":
    # Set random seed for reproducible results
    np.random.seed(42)
    main()