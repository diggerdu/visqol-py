#!/usr/bin/env python3
"""
Build script for native ViSQOL library.

This script attempts to build the native ViSQOL library from source.
If it fails, the package will fall back to the Python-only implementation.
"""

import os
import sys
import subprocess
import shutil
import tempfile
import platform
import urllib.request
from pathlib import Path


def check_system_requirements():
    """Check if system has required tools."""
    print("Checking system requirements...")
    
    required_tools = ['git', 'python3']
    missing_tools = []
    
    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"Missing required tools: {', '.join(missing_tools)}")
        return False
    
    print("✅ System requirements satisfied")
    return True


def install_bazelisk(install_dir):
    """Install Bazelisk (Bazel launcher)."""
    print("Installing Bazelisk...")
    
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    # Normalize architecture names
    if arch in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif arch in ['aarch64', 'arm64']:
        arch = 'arm64'
    else:
        raise RuntimeError(f"Unsupported architecture: {arch}")
    
    # Determine download URL
    if system == 'linux':
        url = f"https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-linux-{arch}"
        binary_name = 'bazel'
    elif system == 'darwin':
        url = f"https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-darwin-{arch}"
        binary_name = 'bazel'
    elif system == 'windows':
        url = f"https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-windows-{arch}.exe"
        binary_name = 'bazel.exe'
    else:
        raise RuntimeError(f"Unsupported system: {system}")
    
    bazel_path = os.path.join(install_dir, binary_name)
    
    print(f"Downloading from: {url}")
    urllib.request.urlretrieve(url, bazel_path)
    
    if system != 'windows':
        os.chmod(bazel_path, 0o755)
    
    print(f"✅ Bazelisk installed to {bazel_path}")
    return bazel_path


def clone_visqol(work_dir):
    """Clone the ViSQOL repository."""
    print("Cloning ViSQOL repository...")
    
    visqol_dir = os.path.join(work_dir, 'visqol')
    
    try:
        subprocess.run([
            'git', 'clone', '--depth=1', '--recursive',
            'https://github.com/google/visqol.git',
            visqol_dir
        ], check=True, capture_output=True, text=True)
        
        print(f"✅ ViSQOL cloned to {visqol_dir}")
        return visqol_dir
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to clone ViSQOL: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        raise


def build_visqol(visqol_dir, bazel_path):
    """Build ViSQOL using Bazel."""
    print("Building ViSQOL with Bazel...")
    
    original_dir = os.getcwd()
    
    try:
        os.chdir(visqol_dir)
        
        # Set up environment
        env = os.environ.copy()
        env['PATH'] = f"{os.path.dirname(bazel_path)}:{env['PATH']}"
        
        # Build commands
        build_commands = [
            # Build protobuf files
            [bazel_path, 'build', '-c', 'opt', '//:similarity_result_py_pb2'],
            [bazel_path, 'build', '-c', 'opt', '//:visqol_config_py_pb2'],
            # Build Python library
            [bazel_path, 'build', '-c', 'opt', '//python:visqol_lib_py.so'],
        ]
        
        for cmd in build_commands:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Build command failed: {' '.join(cmd)}")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd)
        
        print("✅ ViSQOL built successfully")
        
    finally:
        os.chdir(original_dir)


def copy_built_files(visqol_dir, target_dir):
    """Copy built files to package directory."""
    print("Copying built files...")
    
    bazel_bin = os.path.join(visqol_dir, 'bazel-bin')
    
    # Create target directories
    target_dir = Path(target_dir)
    model_dir = target_dir / 'visqol_py' / 'model'
    pb2_dir = target_dir / 'visqol_py' / 'pb2'
    
    model_dir.mkdir(parents=True, exist_ok=True)
    pb2_dir.mkdir(parents=True, exist_ok=True)
    
    files_copied = 0
    
    # Copy Python library
    so_file = os.path.join(bazel_bin, 'python', 'visqol_lib_py.so')
    if os.path.exists(so_file):
        shutil.copy2(so_file, target_dir / 'visqol_py')
        print(f"✅ Copied {so_file}")
        files_copied += 1
    else:
        print(f"⚠️  Python library not found: {so_file}")
    
    # Copy protobuf files
    pb_files = [
        ('similarity_result_py_pb2.py', 'similarity_result_py_pb2.py'),
        ('visqol_config_py_pb2.py', 'visqol_config_py_pb2.py')
    ]
    
    for src_name, dst_name in pb_files:
        src = os.path.join(bazel_bin, src_name)
        if os.path.exists(src):
            shutil.copy2(src, pb2_dir / dst_name)
            print(f"✅ Copied {src_name}")
            files_copied += 1
        else:
            print(f"⚠️  Protobuf file not found: {src}")
    
    # Copy model files
    model_src = os.path.join(visqol_dir, 'model')
    if os.path.exists(model_src):
        for item in os.listdir(model_src):
            src_path = os.path.join(model_src, item)
            if os.path.isfile(src_path) and item.endswith(('.tflite', '.txt', '.model')):
                shutil.copy2(src_path, model_dir)
                print(f"✅ Copied model: {item}")
                files_copied += 1
    
    # Create __init__.py files if they don't exist
    for init_dir in [pb2_dir, model_dir]:
        init_file = init_dir / '__init__.py'
        if not init_file.exists():
            init_file.write_text('# ViSQOL generated files\n')
    
    print(f"✅ Copied {files_copied} files")
    return files_copied > 0


def main():
    """Main build function."""
    print("🚀 Building ViSQOL Native Library")
    print("=" * 50)
    
    if not check_system_requirements():
        print("❌ System requirements not met")
        return False
    
    target_dir = os.getcwd()
    
    with tempfile.TemporaryDirectory() as work_dir:
        try:
            # Install Bazelisk if Bazel not available
            if not shutil.which('bazel'):
                bazel_path = install_bazelisk(work_dir)
            else:
                bazel_path = 'bazel'
                print("✅ Using system Bazel")
            
            # Clone and build ViSQOL
            visqol_dir = clone_visqol(work_dir)
            build_visqol(visqol_dir, bazel_path)
            
            # Copy files to package
            success = copy_built_files(visqol_dir, target_dir)
            
            if success:
                print("🎉 Native ViSQOL build completed successfully!")
                return True
            else:
                print("⚠️  Build completed but no files were copied")
                return False
                
        except Exception as e:
            print(f"❌ Build failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)