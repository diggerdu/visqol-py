#!/usr/bin/env python3
"""
ViSQOL-Py: A Python wrapper for ViSQOL audio quality metrics.

This package provides an easy-to-install Python interface to Google's ViSQOL
(Virtual Speech Quality Objective Listener) metric without requiring manual
Bazel installation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.bdist_wheel import bdist_wheel
import tempfile


def _build_native_library():
    """Build native ViSQOL library - shared function."""
    print("\n" + "="*60, flush=True)
    print("🚀 ViSQOL-Py: Building native ViSQOL library", flush=True)
    print("📋 This process may take 5-15 minutes and includes:", flush=True)
    print("   • Downloading compatible Bazel version", flush=True)
    print("   • Cloning Google's ViSQOL repository", flush=True) 
    print("   • Compiling C++ code with TensorFlow dependencies", flush=True)
    print("   • Installing compiled library", flush=True)
    print("="*60, flush=True)
    
    # Force unbuffered output to see progress in real-time during pip install
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    result = subprocess.run([
        sys.executable, '-u', 'build_native.py'  # -u for unbuffered output
    ], env=env, timeout=3600)  # Let output go directly to terminal
    
    if result.returncode == 0:
        print("✅ Native ViSQOL library built successfully!", flush=True)
        return True
    else:
        print("❌ Native build failed.", flush=True)
        print(f"Exit code: {result.returncode}", flush=True)
        raise RuntimeError("Native ViSQOL build failed. This package requires native library.")


class CustomBuildPy(build_py):
    """Custom build_py that builds native library."""
    
    def run(self):
        # Build native library first
        print("🔧 CustomBuildPy: Building native library...", flush=True)
        _build_native_library()
        
        # Then run normal build_py
        super().run()
        
        # Copy native library to build directory
        build_lib = self.build_lib
        package_dir = os.path.join(build_lib, 'visqol_py')
        
        # Look for the built native library
        so_file = 'visqol_lib_py.so'
        if os.path.exists(so_file):
            print(f"📁 Copying {so_file} to {package_dir}", flush=True)
            os.makedirs(package_dir, exist_ok=True)
            shutil.copy2(so_file, package_dir)
        else:
            raise RuntimeError(f"Native library {so_file} not found after build")


class CustomBdistWheel(bdist_wheel):
    """Custom bdist_wheel that ensures native library is included."""
    
    def run(self):
        print("🎯 CustomBdistWheel: Starting wheel build...", flush=True)
        super().run()
        print("✅ CustomBdistWheel: Wheel build completed", flush=True)


# Use setup() directly instead of relying on pyproject.toml
setup(
    name="visqol-py",
    version="3.3.3", 
    author="Google Research (Original), Wrapper by Community",
    author_email="visqol-py@example.com",
    description="Python wrapper for ViSQOL audio quality metrics",
    long_description=__doc__,
    long_description_content_type="text/plain",
    url="https://github.com/diggerdu/visqol-py",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers", 
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8", 
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.19.0",
        "scipy>=1.7.0",
        "soundfile>=0.10.0",
        "protobuf>=3.19.0,<4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov", 
            "black",
            "isort",
            "mypy",
        ],
        "tensorflow": [
            "tensorflow>=2.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "visqol-py=visqol_py.cli:main",
        ],
    },
    package_data={
        "visqol_py": [
            "*.so",  # Include native library
            "models/*.tflite",
            "models/*.txt", 
            "data/*.wav",
        ],
    },
    include_package_data=True,
    cmdclass={
        "build_py": CustomBuildPy,
        "bdist_wheel": CustomBdistWheel,
    },
    zip_safe=False,
)