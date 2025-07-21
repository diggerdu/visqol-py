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
    print(f"ViSQOL directory: {visqol_dir}")
    print(f"Bazel path: {bazel_path}")
    
    original_dir = os.getcwd()
    
    try:
        os.chdir(visqol_dir)
        print(f"Changed to directory: {os.getcwd()}")
        
        # Set up environment
        env = os.environ.copy()
        env['PATH'] = f"{os.path.dirname(bazel_path)}:{env['PATH']}"
        
        # First, let's sync external dependencies
        print("🔄 Syncing external dependencies...")
        sync_cmd = [bazel_path, 'sync', '--noenable_bzlmod', '--enable_workspace']
        sync_result = subprocess.run(sync_cmd, env=env, capture_output=True, text=True, timeout=300)
        
        if sync_result.returncode == 0:
            print("✅ Dependencies synced successfully")
        else:
            print("⚠️ Dependency sync had issues, but continuing...")
            print(f"Sync stdout: {sync_result.stdout}")
            print(f"Sync stderr: {sync_result.stderr}")
        
        # Now let's check what Bazel targets are available
        print("🔍 Querying available Bazel targets...")
        query_cmd = [bazel_path, 'query', '--noenable_bzlmod', '--enable_workspace', '//...']
        result = subprocess.run(query_cmd, env=env, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("Available targets:")
            targets = result.stdout.strip().split('\n')
            for target in targets[:20]:  # Show first 20 targets
                print(f"  {target}")
            if len(targets) > 20:
                print(f"  ... and {len(targets) - 20} more targets")
        else:
            print("⚠️ Could not query targets, proceeding with build...")
            print(f"Query stdout: {result.stdout}")
            print(f"Query stderr: {result.stderr}")
        
        # Build commands - let's try simpler targets first
        # For Bazel 8+ compatibility, we need to disable bzlmod and force WORKSPACE usage
        build_commands = [
            # Try to build the python bindings directly with WORKSPACE mode
            [bazel_path, 'build', '-c', 'opt', '--verbose_failures', '--noenable_bzlmod', '--enable_workspace', '//python:visqol_lib_py'],
        ]
        
        for cmd in build_commands:
            print(f"🔨 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1200)  # 20 minute timeout
            
            print(f"Command completed with return code: {result.returncode}")
            print(f"📝 Full stdout:\n{result.stdout}")
            print(f"📝 Full stderr:\n{result.stderr}")
            
            if result.returncode != 0:
                print(f"❌ Build command failed: {' '.join(cmd)}")
                
                # Try alternative targets with WORKSPACE mode
                alternative_commands = [
                    [bazel_path, 'build', '-c', 'opt', '--verbose_failures', '--noenable_bzlmod', '--enable_workspace', '//python:all'],
                    [bazel_path, 'build', '-c', 'opt', '--verbose_failures', '--noenable_bzlmod', '--enable_workspace', '//:all'],
                    # Also try building specific targets
                    [bazel_path, 'build', '-c', 'opt', '--verbose_failures', '--noenable_bzlmod', '--enable_workspace', '//python:visqol_lib_py.so'],
                    [bazel_path, 'build', '-c', 'opt', '--verbose_failures', '--noenable_bzlmod', '--enable_workspace', '//src:visqol_api'],
                ]
                
                success = False
                for alt_cmd in alternative_commands:
                    print(f"🔄 Trying alternative: {' '.join(alt_cmd)}")
                    alt_result = subprocess.run(alt_cmd, env=env, capture_output=True, text=True, timeout=1200)
                    
                    print(f"Alternative stdout:\n{alt_result.stdout}")
                    print(f"Alternative stderr:\n{alt_result.stderr}")
                    
                    if alt_result.returncode == 0:
                        print("✅ Alternative build succeeded!")
                        success = True
                        break
                
                if not success:
                    print("❌ All build attempts failed")
                    raise subprocess.CalledProcessError(result.returncode, cmd)
        
        print("✅ ViSQOL built successfully")
        
    except subprocess.TimeoutExpired as e:
        print(f"❌ Build timed out: {e}")
        raise
    finally:
        os.chdir(original_dir)


def copy_built_files(visqol_dir, target_dir):
    """Copy built files to package directory."""
    print("📁 Copying built files...")
    print(f"Source directory: {visqol_dir}")
    print(f"Target directory: {target_dir}")
    
    bazel_bin = os.path.join(visqol_dir, 'bazel-bin')
    print(f"Bazel-bin directory: {bazel_bin}")
    
    # List contents of bazel-bin to see what was actually built
    if os.path.exists(bazel_bin):
        print("📂 Contents of bazel-bin:")
        for root, dirs, files in os.walk(bazel_bin):
            level = root.replace(bazel_bin, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
    else:
        print("❌ bazel-bin directory not found!")
        return False
    
    # Create target directories
    target_dir = Path(target_dir)
    model_dir = target_dir / 'visqol_py' / 'model'
    pb2_dir = target_dir / 'visqol_py' / 'pb2'
    
    model_dir.mkdir(parents=True, exist_ok=True)
    pb2_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directories: {model_dir}, {pb2_dir}")
    
    files_copied = 0
    
    # Look for Python library with different possible names and locations
    possible_so_locations = [
        'python/visqol_lib_py.so',
        'python/visqol_lib_py',
        'visqol_lib_py.so', 
        'python/_pywrap_visqol_lib_py.so',
    ]
    
    so_file_found = None
    for so_path in possible_so_locations:
        full_path = os.path.join(bazel_bin, so_path)
        if os.path.exists(full_path):
            so_file_found = full_path
            break
    
    if so_file_found:
        shutil.copy2(so_file_found, target_dir / 'visqol_py')
        print(f"✅ Copied Python library: {so_file_found}")
        files_copied += 1
    else:
        print("⚠️ Python library (.so file) not found in any expected location")
        # Search for any .so files
        print("🔍 Searching for .so files:")
        for root, dirs, files in os.walk(bazel_bin):
            for file in files:
                if file.endswith('.so'):
                    print(f"  Found .so file: {os.path.join(root, file)}")
    
    # Look for protobuf files in various locations
    possible_pb_locations = [
        '',  # Root of bazel-bin
        'python/',
        'proto/',
    ]
    
    pb_files = [
        'similarity_result_py_pb2.py',
        'visqol_config_py_pb2.py'
    ]
    
    for pb_file in pb_files:
        found = False
        for location in possible_pb_locations:
            src = os.path.join(bazel_bin, location, pb_file)
            if os.path.exists(src):
                shutil.copy2(src, pb2_dir / pb_file)
                print(f"✅ Copied protobuf: {pb_file}")
                files_copied += 1
                found = True
                break
        
        if not found:
            print(f"⚠️ Protobuf file not found: {pb_file}")
    
    # Copy model files
    model_src = os.path.join(visqol_dir, 'model')
    print(f"Looking for model files in: {model_src}")
    
    if os.path.exists(model_src):
        print("📂 Contents of model directory:")
        for item in os.listdir(model_src):
            print(f"  {item}")
            src_path = os.path.join(model_src, item)
            if os.path.isfile(src_path) and item.endswith(('.tflite', '.txt', '.model')):
                shutil.copy2(src_path, model_dir)
                print(f"✅ Copied model: {item}")
                files_copied += 1
    else:
        print("⚠️ Model directory not found")
    
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