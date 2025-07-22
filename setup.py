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
from setuptools.command.develop import develop
from setuptools.command.build_py import build_py
import tempfile


def _build_native_library():
    """Build native ViSQOL library - shared function."""
    import sys
    import os
    
    try:
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
        ], env=env, timeout=3600, stdout=None, stderr=None)  # Direct output to terminal, no capture
        
        if result.returncode == 0:
            print("✅ Native ViSQOL library built successfully!", flush=True)
            return True
        else:
            print("❌ Native build failed.", flush=True)
            print(f"Exit code: {result.returncode}", flush=True)
            raise RuntimeError("Native ViSQOL build failed. This package requires native library.")
                
    except subprocess.TimeoutExpired:
        print("❌ Native build timed out after 1 hour.", flush=True)
        raise RuntimeError("Native ViSQOL build timed out. This package requires native library.")
    except Exception as e:
        print(f"❌ Could not build native ViSQOL: {e}", flush=True)
        raise RuntimeError(f"Native ViSQOL build failed: {e}. This package requires native library.")


class ViSQOLBuildPy(build_py):
    """Custom build_py command that triggers native build."""
    
    def run(self):
        # Build native library first - this runs during wheel creation
        _build_native_library()
        build_py.run(self)


class ViSQOLBuildExt(build_ext):
    """Custom build extension that handles ViSQOL compilation."""
    
    def run(self):
        # Native build is REQUIRED - don't catch exceptions
        _build_native_library()
        
        # Continue with normal build_ext (even if no real extensions)
        build_ext.run(self)
    


class ViSQOLInstall(install):
    """Custom install command."""
    
    def run(self):
        # Native build is REQUIRED - don't catch exceptions
        _build_native_library()
        install.run(self)


class ViSQOLDevelop(develop):
    """Custom develop command."""
    
    def run(self):
        # Build native library before develop
        _build_native_library()
        develop.run(self)


setup(
    name="visqol-py",
    version="3.3.4",
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
        "build_py": ViSQOLBuildPy,
        "build_ext": ViSQOLBuildExt,
        "install": ViSQOLInstall,
        "develop": ViSQOLDevelop,
    },
    # Add a dummy extension to ensure build_ext runs
    ext_modules=[Extension("visqol_py._dummy", sources=[])],
    zip_safe=False,
)