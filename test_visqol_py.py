#!/usr/bin/env python3
"""
Comprehensive test script for ViSQOL-Py package.

This script tests the ViSQOL-Py API functionality using randomly generated
audio samples to ensure the package works correctly after installation.
"""

import sys
import time
import tempfile
import traceback
from pathlib import Path
from typing import List, Tuple, Dict, Any
import warnings

import numpy as np

def generate_sine_wave(frequency: float, duration: float, sample_rate: int, amplitude: float = 0.7) -> np.ndarray:
    """Generate a sine wave signal."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    return amplitude * np.sin(2 * np.pi * frequency * t)

def generate_noise(duration: float, sample_rate: int, amplitude: float = 0.1) -> np.ndarray:
    """Generate white noise."""
    samples = int(sample_rate * duration)
    return amplitude * np.random.randn(samples)

def generate_complex_signal(duration: float, sample_rate: int) -> np.ndarray:
    """Generate a complex signal with multiple harmonics."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Fundamental frequency and harmonics
    fundamental = 440.0  # A4
    signal = (
        0.5 * np.sin(2 * np.pi * fundamental * t) +           # Fundamental
        0.3 * np.sin(2 * np.pi * fundamental * 2 * t) +       # 2nd harmonic
        0.2 * np.sin(2 * np.pi * fundamental * 3 * t) +       # 3rd harmonic
        0.1 * np.sin(2 * np.pi * fundamental * 4 * t)         # 4th harmonic
    )
    
    # Add amplitude modulation to simulate speech-like patterns
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 3 * t))
    signal *= envelope
    
    return signal * 0.7

def apply_degradation(signal: np.ndarray, degradation_type: str, severity: float = 0.1) -> np.ndarray:
    """Apply various types of degradation to a signal."""
    degraded = signal.copy()
    
    if degradation_type == "noise":
        noise = severity * np.random.randn(len(signal))
        degraded = signal + noise
        
    elif degradation_type == "clipping":
        threshold = 1.0 - severity
        degraded = np.clip(signal, -threshold, threshold)
        
    elif degradation_type == "compression":
        # Soft compression using tanh
        gain = 1.0 + severity * 2
        degraded = np.tanh(signal * gain) / gain
        
    elif degradation_type == "lowpass":
        # Simple moving average lowpass filter
        window_size = max(1, int(severity * 100))
        kernel = np.ones(window_size) / window_size
        degraded = np.convolve(signal, kernel, mode='same')
        
    elif degradation_type == "distortion":
        # Harmonic distortion
        degraded = signal + severity * signal**3
        
    elif degradation_type == "amplitude_reduction":
        degraded = signal * (1.0 - severity)
        
    return degraded

class ViSQOLTester:
    """Comprehensive tester for ViSQOL-Py package."""
    
    def __init__(self):
        self.results = []
        self.errors = []
        
    def log_result(self, test_name: str, success: bool, details: str = "", score: float = None):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'success': success,
            'details': details,
            'score': score
        }
        self.results.append(result)
        
        score_info = f" (Score: {score:.3f})" if score is not None else ""
        print(f"{status} {test_name}{score_info}")
        if details and not success:
            print(f"    Details: {details}")
    
    def test_import(self) -> bool:
        """Test package import."""
        try:
            import visqol_py
            version = getattr(visqol_py, '__version__', 'unknown')
            self.log_result("Package Import", True, f"Version: {version}")
            return True
        except Exception as e:
            self.log_result("Package Import", False, str(e))
            return False
    
    def test_basic_api_creation(self) -> bool:
        """Test basic ViSQOL API creation."""
        try:
            import visqol_py
            
            # Test audio mode
            visqol_audio = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.AUDIO)
            audio_mode = visqol_audio.mode.value
            
            # Test speech mode
            visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
            speech_mode = visqol_speech.mode.value
            
            self.log_result("API Creation", True, 
                          f"Audio mode: {audio_mode}, Speech mode: {speech_mode}")
            return True
        except Exception as e:
            self.log_result("API Creation", False, str(e))
            return False
    
    def test_identical_signals(self) -> bool:
        """Test with identical reference and degraded signals."""
        try:
            import visqol_py
            
            # Generate test signal
            duration = 3.0
            sample_rate = 48000
            signal = generate_sine_wave(440, duration, sample_rate)
            
            # Test with identical signals
            visqol = visqol_py.ViSQOL()
            result = visqol.measure(signal, signal)
            
            # Identical signals should have high quality scores
            success = result.moslqo >= 3.5  # Expect high score for identical signals
            self.log_result("Identical Signals", success, 
                          f"Expected >= 3.5, got {result.moslqo:.3f}", result.moslqo)
            return success
        except Exception as e:
            self.log_result("Identical Signals", False, str(e))
            return False
    
    def test_degradation_detection(self) -> bool:
        """Test detection of various degradations."""
        try:
            import visqol_py
            
            duration = 4.0
            sample_rate = 48000
            reference = generate_complex_signal(duration, sample_rate)
            
            visqol = visqol_py.ViSQOL()
            degradation_scores = {}
            
            # Test different degradation types
            degradations = [
                ("clean", 0.0),
                ("light_noise", 0.05),
                ("heavy_noise", 0.2),
                ("clipping", 0.3),
                ("compression", 0.4),
                ("distortion", 0.2)
            ]
            
            for deg_name, severity in degradations:
                if deg_name == "clean":
                    degraded = reference
                else:
                    deg_type = deg_name.split('_')[0] if '_' in deg_name else deg_name
                    degraded = apply_degradation(reference, deg_type, severity)
                
                result = visqol.measure(reference, degraded)
                degradation_scores[deg_name] = result.moslqo
            
            # Check if scores decrease with degradation severity
            clean_score = degradation_scores["clean"]
            light_noise_score = degradation_scores["light_noise"]
            heavy_noise_score = degradation_scores["heavy_noise"]
            
            # Scores should generally decrease with increased degradation
            trend_correct = clean_score >= light_noise_score >= heavy_noise_score
            
            details = f"Scores: {', '.join([f'{k}={v:.3f}' for k, v in degradation_scores.items()])}"
            self.log_result("Degradation Detection", trend_correct, details)
            
            return trend_correct
        except Exception as e:
            self.log_result("Degradation Detection", False, str(e))
            return False
    
    def test_speech_mode(self) -> bool:
        """Test speech mode functionality."""
        try:
            import visqol_py
            
            # Generate speech-like signal at 16kHz
            duration = 5.0
            sample_rate = 16000
            
            # Create speech-like signal with formants
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # Simulate formants (typical speech frequencies)
            f1, f2, f3 = 800, 1200, 2500  # Typical formant frequencies
            speech_signal = (
                0.4 * np.sin(2 * np.pi * f1 * t) +
                0.3 * np.sin(2 * np.pi * f2 * t) +
                0.2 * np.sin(2 * np.pi * f3 * t)
            )
            
            # Add speech-like amplitude modulation
            envelope = 0.5 * (1 + np.sin(2 * np.pi * 4 * t))  # 4 Hz modulation
            speech_signal *= envelope
            
            # Add slight degradation
            degraded_speech = speech_signal + 0.05 * np.random.randn(len(speech_signal))
            
            # Test with speech mode
            visqol_speech = visqol_py.ViSQOL(mode=visqol_py.ViSQOLMode.SPEECH)
            result = visqol_speech.measure(speech_signal, degraded_speech)
            
            # Should produce a reasonable score
            success = 1.0 <= result.moslqo <= 5.0
            self.log_result("Speech Mode", success, 
                          f"Score: {result.moslqo:.3f}", result.moslqo)
            return success
        except Exception as e:
            self.log_result("Speech Mode", False, str(e))
            return False
    
    def test_batch_processing(self) -> bool:
        """Test batch processing functionality."""
        try:
            import visqol_py
            
            duration = 2.0
            sample_rate = 48000
            visqol = visqol_py.ViSQOL()
            
            # Create multiple test signal pairs
            test_pairs = []
            frequencies = [220, 440, 880]  # Different frequencies
            noise_levels = [0.02, 0.05, 0.1]  # Different noise levels
            
            for i, (freq, noise) in enumerate(zip(frequencies, noise_levels)):
                reference = generate_sine_wave(freq, duration, sample_rate)
                degraded = reference + noise * np.random.randn(len(reference))
                test_pairs.append((reference, degraded))
            
            # Test batch processing
            results = []
            for ref, deg in test_pairs:
                result = visqol.measure(ref, deg)
                results.append(result)
            
            # All results should be valid
            all_valid = all(1.0 <= result.moslqo <= 5.0 for result in results)
            scores = [f"{result.moslqo:.3f}" for result in results]
            
            self.log_result("Batch Processing", all_valid, 
                          f"Scores: {', '.join(scores)}")
            return all_valid
        except Exception as e:
            self.log_result("Batch Processing", False, str(e))
            return False
    
    def test_edge_cases(self) -> bool:
        """Test edge cases and error handling."""
        try:
            import visqol_py
            
            duration = 1.0
            sample_rate = 48000
            visqol = visqol_py.ViSQOL()
            
            edge_cases_passed = 0
            total_edge_cases = 0
            
            # Test 1: Very short signals
            total_edge_cases += 1
            try:
                short_signal = generate_sine_wave(440, 0.1, sample_rate)  # 0.1 second
                result = visqol.measure(short_signal, short_signal)
                if 1.0 <= result.moslqo <= 5.0:
                    edge_cases_passed += 1
            except Exception:
                pass  # Expected to potentially fail
            
            # Test 2: Different signal lengths
            total_edge_cases += 1
            try:
                ref_signal = generate_sine_wave(440, 2.0, sample_rate)
                deg_signal = generate_sine_wave(440, 1.5, sample_rate)
                result = visqol.measure(ref_signal, deg_signal)
                if 1.0 <= result.moslqo <= 5.0:
                    edge_cases_passed += 1
            except Exception:
                pass  # Expected to potentially fail
            
            # Test 3: Very quiet signals
            total_edge_cases += 1
            try:
                quiet_signal = generate_sine_wave(440, duration, sample_rate, amplitude=0.001)
                result = visqol.measure(quiet_signal, quiet_signal)
                if 1.0 <= result.moslqo <= 5.0:
                    edge_cases_passed += 1
            except Exception:
                pass  # Expected to potentially fail
            
            # Test 4: Signals with different content
            total_edge_cases += 1
            try:
                sine_signal = generate_sine_wave(440, duration, sample_rate)
                noise_signal = generate_noise(duration, sample_rate, amplitude=0.1)
                result = visqol.measure(sine_signal, noise_signal)
                if 1.0 <= result.moslqo <= 5.0:
                    edge_cases_passed += 1
            except Exception:
                pass  # Expected to potentially fail
            
            success = edge_cases_passed >= total_edge_cases // 2  # At least half should work
            self.log_result("Edge Cases", success, 
                          f"Passed {edge_cases_passed}/{total_edge_cases} edge cases")
            return success
        except Exception as e:
            self.log_result("Edge Cases", False, str(e))
            return False
    
    def test_performance_benchmark(self) -> bool:
        """Test performance with timing benchmarks."""
        try:
            import visqol_py
            
            durations = [1.0, 3.0, 5.0]  # Different signal lengths
            sample_rate = 48000
            visqol = visqol_py.ViSQOL()
            
            timing_results = []
            
            for duration in durations:
                # Generate test signals
                reference = generate_complex_signal(duration, sample_rate)
                degraded = apply_degradation(reference, "noise", 0.05)
                
                # Measure timing
                start_time = time.time()
                result = visqol.measure(reference, degraded)
                end_time = time.time()
                
                processing_time = end_time - start_time
                real_time_factor = processing_time / duration
                
                timing_results.append({
                    'duration': duration,
                    'processing_time': processing_time,
                    'real_time_factor': real_time_factor,
                    'score': result.moslqo
                })
            
            # Performance should be reasonable (subjective, but under 10x real-time for fallback)
            avg_rt_factor = np.mean([r['real_time_factor'] for r in timing_results])
            performance_good = avg_rt_factor < 10.0  # Fallback implementation may be slower
            
            time_list = [f'{r["processing_time"]:.2f}s' for r in timing_results]
            timing_details = f"Avg RT factor: {avg_rt_factor:.2f}x, Times: {time_list}"
            
            self.log_result("Performance Benchmark", performance_good, timing_details)
            return performance_good
        except Exception as e:
            self.log_result("Performance Benchmark", False, str(e))
            return False
    
    def test_result_structure(self) -> bool:
        """Test the structure and content of ViSQOLResult objects."""
        try:
            import visqol_py
            
            duration = 3.0
            sample_rate = 48000
            reference = generate_sine_wave(440, duration, sample_rate)
            degraded = apply_degradation(reference, "noise", 0.05)
            
            visqol = visqol_py.ViSQOL()
            result = visqol.measure(reference, degraded)
            
            # Check result structure
            checks = []
            checks.append(hasattr(result, 'moslqo'))
            checks.append(hasattr(result, 'vnsim'))
            checks.append(hasattr(result, 'fvnsim'))
            checks.append(hasattr(result, 'center_freq_bands'))
            checks.append(isinstance(result.moslqo, (int, float)))
            checks.append(1.0 <= result.moslqo <= 5.0)
            
            # Check string representation
            result_str = str(result)
            checks.append('MOS-LQO' in result_str)
            checks.append('VNSIM' in result_str)
            
            all_checks_passed = all(checks)
            
            details = f"MOS-LQO: {result.moslqo:.3f}, VNSIM: {result.vnsim:.3f}, " + \
                     f"Attributes: {len([attr for attr in dir(result) if not attr.startswith('_')])}"
            
            self.log_result("Result Structure", all_checks_passed, details, result.moslqo)
            return all_checks_passed
        except Exception as e:
            self.log_result("Result Structure", False, str(e))
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary."""
        print("=" * 60)
        print("🧪 ViSQOL-Py Comprehensive Test Suite")
        print("=" * 60)
        print("Testing with randomly generated audio samples...")
        print()
        
        # Suppress warnings during testing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Core functionality tests
            tests = [
                self.test_import,
                self.test_basic_api_creation,
                self.test_identical_signals,
                self.test_degradation_detection,
                self.test_speech_mode,
                self.test_batch_processing,
                self.test_edge_cases,
                self.test_result_structure,
                self.test_performance_benchmark,
            ]
            
            print("Running tests...")
            print("-" * 40)
            
            for test_func in tests:
                try:
                    test_func()
                except Exception as e:
                    test_name = test_func.__name__.replace('test_', '').replace('_', ' ').title()
                    self.log_result(test_name, False, f"Unexpected error: {str(e)}")
                    self.errors.append(traceback.format_exc())
        
        # Generate summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print()
        print("=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print()
            print("❌ Failed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        # Performance summary
        scores = [r['score'] for r in self.results if r['score'] is not None]
        if scores:
            print()
            print(f"📈 Score Statistics:")
            print(f"  Mean Score: {np.mean(scores):.3f}")
            print(f"  Score Range: {np.min(scores):.3f} - {np.max(scores):.3f}")
        
        print()
        if failed_tests == 0:
            print("🎉 All tests passed! ViSQOL-Py is working correctly.")
        elif passed_tests >= total_tests * 0.8:
            print("⚠️  Most tests passed. Package is functional with some limitations.")
        else:
            print("🚨 Multiple test failures. Please check the installation.")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'results': self.results,
            'errors': self.errors
        }

def main():
    """Main test function."""
    try:
        print("🚀 Starting ViSQOL-Py Test Suite")
        print(f"Python version: {sys.version}")
        print(f"NumPy version: {np.__version__}")
        print()
        
        # Set random seed for reproducible tests
        np.random.seed(42)
        
        # Run tests
        tester = ViSQOLTester()
        summary = tester.run_all_tests()
        
        # Exit with appropriate code
        if summary['failed'] == 0:
            sys.exit(0)
        elif summary['success_rate'] >= 80:
            sys.exit(1)  # Partial success
        else:
            sys.exit(2)  # Major failures
            
    except Exception as e:
        print(f"🚨 Critical error running tests: {e}")
        traceback.print_exc()
        sys.exit(3)

if __name__ == "__main__":
    main()