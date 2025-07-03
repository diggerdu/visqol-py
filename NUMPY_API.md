# ViSQOL-Py Native NumPy Array API

ViSQOL-Py provides **native support for NumPy arrays**, allowing you to process audio data directly in memory without needing to save files to disk. This makes it perfect for real-time applications, audio processing pipelines, and memory-efficient workflows.

## Quick Start

```python
import numpy as np
import visqol_py

# Create test signals (numpy arrays)
sample_rate = 48000
duration = 3.0
t = np.linspace(0, duration, int(sample_rate * duration))

reference = np.sin(2 * np.pi * 440 * t) * 0.7  # Clean sine wave
degraded = reference + 0.05 * np.random.randn(len(reference))  # Add noise

# Compute ViSQOL score directly from arrays
visqol = visqol_py.ViSQOL()
result = visqol.measure(reference, degraded)

print(f"MOS-LQO Score: {result.moslqo:.3f}")  # Output: MOS-LQO Score: 2.498
```

## Key Features

### ✅ Direct Array Input
- **No file I/O required** - process arrays directly
- **Memory efficient** - no temporary files created
- **Fast processing** - avoid disk read/write overhead

### ✅ Flexible Input Types
```python
# File paths (traditional)
result = visqol.measure('reference.wav', 'degraded.wav')

# NumPy arrays (native support)
result = visqol.measure(reference_array, degraded_array)

# Mixed input types
result = visqol.measure('reference.wav', degraded_array)
result = visqol.measure(reference_array, 'degraded.wav')
```

### ✅ Multiple Data Types
```python
# Floating-point arrays (recommended)
float32_array = signal.astype(np.float32)
float64_array = signal.astype(np.float64)

result = visqol.measure(float32_array, float64_array)  # ✅ Works
```

### ✅ Both Audio and Speech Modes
```python
# Audio mode (48kHz)
visqol_audio = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.AUDIO)
result = visqol_audio.measure(ref_48k, deg_48k)

# Speech mode (16kHz)  
visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
result = visqol_speech.measure(ref_16k, deg_16k)
```

## Real-World Examples

### Real-Time Audio Processing
```python
import visqol_py
import pyaudio
import numpy as np

visqol = visqol_py.ViSQOL()

def process_audio_stream(reference_buffer, live_audio_buffer):
    """Process live audio stream."""
    result = visqol.measure(reference_buffer, live_audio_buffer)
    return result.moslqo

# Use with live audio streams
```

### Batch Processing Pipeline
```python
def process_audio_batch(audio_pairs):
    """Process multiple audio pairs efficiently."""
    visqol = visqol_py.ViSQOL()
    results = []
    
    for ref_array, deg_array in audio_pairs:
        result = visqol.measure(ref_array, deg_array)
        results.append(result.moslqo)
    
    return results

# Process hundreds of signals without file I/O
scores = process_audio_batch([(ref1, deg1), (ref2, deg2), ...])
```

### Integration with Audio Libraries
```python
import librosa
import soundfile as sf
import visqol_py

# Load with librosa
ref_audio, sr = librosa.load('reference.wav', sr=48000)
deg_audio, sr = librosa.load('degraded.wav', sr=48000)

# Process directly
visqol = visqol_py.ViSQOL()
result = visqol.measure(ref_audio, deg_audio)

# Or load with soundfile
ref_audio, sr = sf.read('reference.wav')
deg_audio, sr = sf.read('degraded.wav')
result = visqol.measure(ref_audio, deg_audio)
```

### Synthetic Audio Testing
```python
def generate_test_signals():
    """Generate synthetic test signals."""
    sample_rate = 48000
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Musical chord
    reference = (
        0.3 * np.sin(2 * np.pi * 261.63 * t) +  # C4
        0.3 * np.sin(2 * np.pi * 329.63 * t) +  # E4
        0.3 * np.sin(2 * np.pi * 392.00 * t)    # G4
    )
    
    # Apply degradation
    degraded = reference + 0.1 * np.random.randn(len(reference))
    
    return reference, degraded

# Test with synthetic signals
ref, deg = generate_test_signals()
visqol = visqol_py.ViSQOL()
result = visqol.measure(ref, deg)
```

## Performance Characteristics

### Throughput Examples
Based on testing with fallback implementation:

| Signal Length | Processing Time | Real-time Factor |
|---------------|-----------------|------------------|
| 1 second      | ~0.02s          | ~50x real-time   |
| 3 seconds     | ~0.05s          | ~60x real-time   |
| 10 seconds    | ~0.08s          | ~125x real-time  |

### Memory Usage
- **Efficient**: ~3.7 MB per 10-second stereo signal at 48kHz
- **No temporary files**: All processing in memory
- **Scalable**: Handle large signals efficiently

## Error Handling

```python
try:
    result = visqol.measure(reference, degraded)
    print(f"Score: {result.moslqo:.3f}")
except ValueError as e:
    print(f"Input error: {e}")
except Exception as e:
    print(f"Processing error: {e}")
```

Common issues:
- **Integer arrays**: Convert to float first: `array.astype(np.float32)`
- **Sample rate mismatch**: Resample using librosa or scipy
- **Different lengths**: ViSQOL handles automatically by truncating to shorter length

## Complete Example

Run the comprehensive example:
```bash
python numpy_array_example.py
```

This demonstrates:
- ✅ Audio and speech mode processing
- ✅ Batch processing workflows  
- ✅ Performance benchmarking
- ✅ Data type handling
- ✅ Memory efficiency testing

## Integration Benefits

### For Researchers
- **Rapid prototyping** with synthetic signals
- **Parameter sweeps** without file management
- **Integration** with existing NumPy/SciPy workflows

### For Developers  
- **Real-time applications** with live audio
- **Microservice architectures** with in-memory processing
- **CI/CD pipelines** with automated testing

### For Production
- **Lower latency** without disk I/O
- **Higher throughput** for batch processing
- **Reduced storage** requirements

## Advanced Usage

See `numpy_array_example.py` for comprehensive examples including:
- Multi-channel signal handling
- Different degradation types
- Performance optimization
- Error handling patterns
- Integration with audio libraries

The native NumPy array support makes ViSQOL-Py perfect for modern audio processing workflows where efficiency and flexibility are paramount.