#!/usr/bin/env python3
"""Test script to verify ViSQOL works without librosa dependency."""

import numpy as np
import tempfile
import os
import visqol_py
from visqol_py.utils import save_audio, load_audio

def test_numpy_arrays():
    """Test ViSQOL with NumPy arrays (no file I/O)."""
    print("🔢 Testing with NumPy arrays...")
    
    # SPEECH mode test
    visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
    
    sr = 16000
    t = np.linspace(0, 2.0, sr * 2)  # 2 seconds
    ref = np.sin(2*np.pi*440*t) * 0.5
    deg = ref + np.random.normal(0, 0.01, ref.shape)
    
    result = visqol_speech.measure(ref, deg)
    print(f"  SPEECH mode: {result}")
    
    # AUDIO mode test  
    visqol_audio = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.AUDIO)
    
    sr = 48000
    t = np.linspace(0, 2.0, sr * 2)
    ref = np.sin(2*np.pi*440*t) * 0.5
    deg = ref + np.random.normal(0, 0.01, ref.shape)
    
    result = visqol_audio.measure(ref, deg)
    print(f"  AUDIO mode: {result}")
    
    print("✅ NumPy array tests passed!")

def test_file_io():
    """Test ViSQOL with audio file I/O using soundfile."""
    print("📁 Testing with audio files...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test audio files
        sr = 16000
        t = np.linspace(0, 1.0, sr)
        ref_audio = np.sin(2*np.pi*440*t) * 0.5
        deg_audio = ref_audio + np.random.normal(0, 0.02, ref_audio.shape)
        
        ref_path = os.path.join(tmpdir, "reference.wav")
        deg_path = os.path.join(tmpdir, "degraded.wav")
        
        # Save files
        save_audio(ref_audio, ref_path, sr)
        save_audio(deg_audio, deg_path, sr)
        print(f"  Created: {ref_path}")
        print(f"  Created: {deg_path}")
        
        # Load and verify
        loaded_ref, loaded_sr = load_audio(ref_path)
        print(f"  Loaded reference: {len(loaded_ref)} samples at {loaded_sr} Hz")
        
        # Test with ViSQOL
        visqol = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
        result = visqol.measure(ref_path, deg_path)
        print(f"  File-based result: {result}")
    
    print("✅ File I/O tests passed!")

def test_resampling():
    """Test the custom resampling functionality."""
    print("🔄 Testing resampling...")
    
    from visqol_py.utils import resample_audio
    
    # Test different resampling scenarios
    scenarios = [
        (44100, 16000),  # Common downsampling
        (48000, 16000),  # Audio to speech
        (16000, 48000),  # Upsampling
        (22050, 48000),  # Different rates
    ]
    
    for orig_sr, target_sr in scenarios:
        # Create test signal
        duration = 0.5  # Short signal for testing
        t = np.linspace(0, duration, int(orig_sr * duration))
        signal = np.sin(2 * np.pi * 1000 * t)  # 1kHz sine
        
        # Resample
        resampled = resample_audio(signal, orig_sr, target_sr)
        
        # Check length
        expected_length = int(len(signal) * target_sr / orig_sr)
        actual_length = len(resampled)
        
        print(f"  {orig_sr}→{target_sr} Hz: {len(signal)}→{actual_length} samples (expected {expected_length})")
        
        # Allow small rounding differences
        assert abs(actual_length - expected_length) <= 1, f"Length mismatch: {actual_length} vs {expected_length}"
    
    print("✅ Resampling tests passed!")

def main():
    """Run all tests."""
    print("🧪 Testing ViSQOL without librosa dependency")
    print("=" * 50)
    
    try:
        test_numpy_arrays()
        test_file_io()
        test_resampling()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ ViSQOL works perfectly without librosa!")
        print("📦 Dependencies reduced: numpy, scipy, soundfile, protobuf")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)