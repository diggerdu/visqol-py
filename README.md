# ViSQOL-Py

A Python wrapper for Google's ViSQOL (Virtual Speech Quality Objective Listener) that can be installed directly from GitHub without requiring manual Bazel installation.

## Features

- **Easy Installation**: Install directly with `pip install git+https://github.com/diggerdu/visqol-py.git`
- **No Bazel Required**: Automatic dependency handling without manual Bazel installation
- **Native NumPy Support**: Process audio arrays directly without file I/O
- **Fallback Implementation**: Works even without native ViSQOL compiled binaries
- **Command Line Interface**: Easy-to-use CLI for batch processing
- **Python API**: Clean Python interface for integration into your projects
- **Dual Mode Support**: Both Audio (48kHz) and Speech (16kHz) modes

## Installation

### Direct from GitHub
```bash
pip install git+https://github.com/diggerdu/visqol-py.git
```

**⚠️ Important**: The installation will attempt to build the native ViSQOL library automatically. If this fails (due to missing dependencies like Bazel), it will fall back to a Python-only implementation that provides reasonable approximations.

### For Best Results (Native ViSQOL)
To get the most accurate results, ensure you have build dependencies:

**Linux/Mac:**
```bash
# Install system dependencies first
sudo apt-get install git build-essential  # Ubuntu/Debian
# or
brew install git  # macOS

# Then install the package (will auto-build native library)
pip install git+https://github.com/diggerdu/visqol-py.git
```

**Manual Native Build:**
```bash
git clone https://github.com/diggerdu/visqol-py.git
cd visqol-py
python build_native.py  # Build native library manually
pip install -e .        # Install package
```

### Development Installation
```bash
git clone https://github.com/diggerdu/visqol-py.git
cd visqol-py
pip install -e .
```

## Quick Start

### Python API

```python
import visqol_py
import numpy as np

# Initialize ViSQOL (default: audio mode)
visqol = visqol_py.ViSQOL()

# Method 1: Compare audio files
result = visqol.measure('reference.wav', 'degraded.wav')
print(f"MOS-LQO Score: {result.moslqo:.3f}")

# Method 2: Compare NumPy arrays directly (no file I/O needed!)
sample_rate = 48000
duration = 3.0
t = np.linspace(0, duration, int(sample_rate * duration))
reference = np.sin(2 * np.pi * 440 * t) * 0.7  # Clean signal
degraded = reference + 0.05 * np.random.randn(len(reference))  # Add noise

result = visqol.measure(reference, degraded)
print(f"Array MOS-LQO: {result.moslqo:.3f}")

# Speech mode
visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
result = visqol_speech.measure('ref_speech.wav', 'deg_speech.wav')
print(f"Speech MOS-LQO: {result.moslqo:.3f}")

# Batch processing
file_pairs = [
    ('ref1.wav', 'deg1.wav'),
    ('ref2.wav', 'deg2.wav'),
]
results = visqol.measure_batch(file_pairs, output_csv='results.csv')
```

### Command Line Interface

```bash
# Compare two files
visqol-py --reference_file ref.wav --degraded_file deg.wav --verbose

# Batch processing
visqol-py --batch_input_csv input.csv --results_csv output.csv

# Speech mode
visqol-py --reference_file ref.wav --degraded_file deg.wav --use_speech_mode --verbose
```

## API Reference

### ViSQOL Class

```python
class ViSQOL:
    def __init__(self, mode: ViSQOLMode = ViSQOLMode.AUDIO)
    def measure(self, reference, degraded) -> ViSQOLResult
    def measure_batch(self, file_pairs, output_csv=None) -> List[ViSQOLResult]
```

### ViSQOLResult

```python
@dataclass
class ViSQOLResult:
    moslqo: float                    # MOS-LQO score (1.0 - 5.0)
    vnsim: float                     # VNSIM score
    fvnsim: List[float]             # Per-frequency band scores
    center_freq_bands: List[float]   # Center frequencies
    reference_path: Optional[str]    # Reference file path
    degraded_path: Optional[str]     # Degraded file path
```

### Modes

- **ViSQOLMode.AUDIO**: 48kHz full-band audio analysis
- **ViSQOLMode.SPEECH**: 16kHz speech analysis with voice activity detection

## Batch Processing

Create a CSV file with reference and degraded file pairs:

```csv
reference,degraded
ref1.wav,deg1.wav
ref2.wav,deg2.wav
ref3.wav,deg3.wav
```

Then run:
```bash
visqol-py --batch_input_csv input.csv --results_csv output.csv
```

## Testing

### Quick Test
Run the comprehensive test suite to verify installation:
```bash
python test_visqol_py.py
```

### Simple Example
Try the basic usage example:
```bash
python example_usage.py
```

### Package Tests
Run the built-in unit tests:
```bash
python -m pytest visqol_py/tests/
```

## 🔢 Native NumPy Array Support

ViSQOL-Py provides **native support for NumPy arrays**, enabling direct processing without file I/O:

```python
import numpy as np
import visqol_py

# Generate test signals
sample_rate = 48000
t = np.linspace(0, 3.0, int(sample_rate * 3.0))
reference = np.sin(2 * np.pi * 440 * t) * 0.7
degraded = reference + 0.05 * np.random.randn(len(reference))

# Process arrays directly
visqol = visqol_py.ViSQOL()
result = visqol.measure(reference, degraded)  # No file I/O needed!
print(f"MOS-LQO: {result.moslqo:.3f}")
```

**Benefits:**
- ⚡ **Faster processing** - no disk I/O overhead
- 💾 **Memory efficient** - no temporary files
- 🔄 **Real-time capable** - perfect for live audio processing
- 🧪 **Research friendly** - ideal for synthetic signal testing

**Use Cases:**
- Real-time audio quality monitoring
- Integration with audio processing pipelines
- Automated testing with synthetic signals
- Research and development workflows

See [NUMPY_API.md](NUMPY_API.md) for comprehensive examples and [numpy_array_example.py](numpy_array_example.py) for a complete demonstration.

## Native vs Fallback Implementation

This wrapper attempts to use the native ViSQOL implementation when available, falling back to an approximation method when not:

- **Native**: Full ViSQOL implementation with official models
- **Fallback**: Spectral similarity approximation using librosa

The fallback implementation provides reasonable estimates but may not match official ViSQOL scores exactly.

## Requirements

- Python 3.7+
- NumPy
- SciPy
- librosa
- soundfile

## Audio Format Support

Supports all formats handled by librosa/soundfile:
- WAV, FLAC, MP3, OGG, etc.
- Mono and stereo (automatically converted to mono)
- Various sample rates (automatically resampled)

## Guidelines

- **Input Duration**: 5-10 seconds of audio recommended
- **Reference Quality**: Should be clean and high quality
- **Sample Rates**: 48kHz for audio mode, 16kHz for speech mode
- **Silence**: Minimize silence at beginning/end of files

## Examples

Check out the [examples.py](visqol_py/examples.py) file for comprehensive usage examples including:
- Basic usage with synthetic signals
- Speech mode processing
- File-based processing
- Batch processing
- Parameter exploration

## Troubleshooting

### ImportError: Native ViSQOL not available
This is normal - the package will use the fallback implementation. For full compatibility, install the original ViSQOL package.

### Audio Loading Errors
Ensure audio files are in supported formats and not corrupted. Use `librosa.load()` to test file loading.

### Memory Issues
For large batch processing, consider processing files in smaller chunks or using lower quality settings.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

Apache License 2.0 - see LICENSE file for details.

## Acknowledgments

- Google Research for the original ViSQOL implementation
- The librosa team for audio processing tools
- Contributors to the open-source audio processing ecosystem