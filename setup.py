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
        """Build ViSQOL from source using system dependencies."""
        try:
            # Check for required system dependencies
            self._check_dependencies()
            
            # Clone and build the original ViSQOL repository
            self._build_visqol()
            
        except Exception as e:
            print(f"Warning: Could not build native ViSQOL: {e}")
            print("Continuing with fallback implementation.")
            print("For full compatibility, consider installing the original ViSQOL package.")
    
    def _check_dependencies(self):
        """Check for required system dependencies."""
        # Check for basic build tools
        required_tools = ['git', 'python3']
        for tool in required_tools:
            if not shutil.which(tool):
                raise RuntimeError(f"Required tool '{tool}' not found in PATH")
    
    def _build_visqol(self):
        """Build ViSQOL using alternative methods."""
        # This is a simplified approach - in practice you might:
        # 1. Use pre-compiled binaries for common platforms
        # 2. Use cmake instead of bazel
        # 3. Use system libraries where possible
        
        print("Building ViSQOL from source...")
        print("Note: This is a placeholder implementation.")
        print("For production use, consider using pre-built wheels or Docker.")


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