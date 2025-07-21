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
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
import tempfile


class ViSQOLBuildExt(build_ext):
    """Custom build extension that handles ViSQOL compilation."""
    
    def run(self):
        # Check if we can use pre-built binaries first
        if self._try_prebuilt():
            return
        
        # Fall back to building from source
        self._build_from_source()
    
    def _try_prebuilt(self):
        """Try to use pre-built binaries if available."""
        # For now, we'll focus on building from source
        # In a real implementation, you might include pre-built wheels
        return False
    
    def _build_from_source(self):
        """Build ViSQOL from source using build script."""
        try:
            print("Attempting to build native ViSQOL library...")
            
            # Run the build script
            import subprocess
            result = subprocess.run([
                sys.executable, 'build_native.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
            
            if result.returncode == 0:
                print("✅ Native ViSQOL library built successfully!")
                print("The package will use native implementation when available.")
            else:
                print("❌ Native build failed.")
                if result.stdout:
                    print("Build output:", result.stdout[-500:])  # Last 500 chars
                if result.stderr:
                    print("Build errors:", result.stderr[-500:])
                raise RuntimeError("Native ViSQOL build failed. This package requires native library.")
                    
        except subprocess.TimeoutExpired:
            print("❌ Native build timed out.")
            raise RuntimeError("Native ViSQOL build timed out. This package requires native library.")
        except Exception as e:
            print(f"❌ Could not build native ViSQOL: {e}")
            raise RuntimeError(f"Native ViSQOL build failed: {e}. This package requires native library.")
    


class ViSQOLInstall(install):
    """Custom install command."""
    
    def run(self):
        install.run(self)


setup(
    name="visqol-py",
    version="3.3.3",
    author="Google Research (Original), Wrapper by Community",
    author_email="",
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
        "librosa>=0.8.0",
        "soundfile>=0.10.0",
        "protobuf>=3.19.0",
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
            "models/*.tflite",
            "models/*.txt",
            "data/*.wav",
        ],
    },
    include_package_data=True,
    cmdclass={
        "build_ext": ViSQOLBuildExt,
        "install": ViSQOLInstall,
    },
    zip_safe=False,
)