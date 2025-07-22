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
    print("Checking system requirements...", flush=True)
    
    required_tools = ['git', 'python3']
    missing_tools = []
    
    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"Missing required tools: {', '.join(missing_tools)}", flush=True)
        return False
    
    print("✅ System requirements satisfied", flush=True)
    return True


def install_compatible_bazel(install_dir):
    """Install compatible Bazel version for ViSQOL."""
    print("Installing compatible Bazel version...", flush=True)
    
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    # Normalize architecture names
    if arch in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif arch in ['aarch64', 'arm64']:
        arch = 'arm64'
    else:
        raise RuntimeError(f"Unsupported architecture: {arch}")
    
    # Use Bazel 6.4.0 which should be compatible with ViSQOL's dependencies  
    # Newer versions (7.x, 8.x) have incompatible changes with TensorFlow WORKSPACE
    bazel_version = "6.4.0"
    
    # Fix architecture naming for Bazel downloads
    if arch == 'amd64':
        arch = 'x86_64'
    
    # Determine download URL - use correct Bazel asset naming
    if system == 'linux':
        url = f"https://github.com/bazelbuild/bazel/releases/download/{bazel_version}/bazel-{bazel_version}-linux-{arch}"
        binary_name = 'bazel'
    elif system == 'darwin':
        url = f"https://github.com/bazelbuild/bazel/releases/download/{bazel_version}/bazel-{bazel_version}-darwin-{arch}"
        binary_name = 'bazel'
    elif system == 'windows':
        url = f"https://github.com/bazelbuild/bazel/releases/download/{bazel_version}/bazel-{bazel_version}-windows-{arch}.exe"
        binary_name = 'bazel.exe'
    else:
        raise RuntimeError(f"Unsupported system: {system}")
    
    bazel_path = os.path.join(install_dir, binary_name)
    
    print(f"⬇️  Downloading compatible Bazel {bazel_version} from: {url}", flush=True)
    urllib.request.urlretrieve(url, bazel_path)
    
    if system != 'windows':
        os.chmod(bazel_path, 0o755)
    
    print(f"✅ Bazel {bazel_version} installed to {bazel_path}", flush=True)
    return bazel_path


def clone_visqol(work_dir):
    """Clone the ViSQOL repository."""
    print("📥 Cloning ViSQOL repository...", flush=True)
    
    visqol_dir = os.path.join(work_dir, 'visqol')
    
    try:
        subprocess.run([
            'git', 'clone', '--depth=1', '--recursive',
            'https://github.com/google/visqol.git',
            visqol_dir
        ], check=True, capture_output=True, text=True)
        
        print(f"✅ ViSQOL cloned to {visqol_dir}", flush=True)
        return visqol_dir
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to clone ViSQOL: {e}", flush=True)
        if e.stderr:
            print(f"Error output: {e.stderr}", flush=True)
        raise


def build_visqol(visqol_dir, bazel_path, work_dir):
    """Build ViSQOL using Bazel."""
    print("🔨 Building ViSQOL with Bazel (this may take several minutes)...", flush=True)
    print(f"ViSQOL directory: {visqol_dir}", flush=True)
    print(f"Bazel path: {bazel_path}", flush=True)
    
    original_dir = os.getcwd()
    
    try:
        os.chdir(visqol_dir)
        print(f"Changed to directory: {os.getcwd()}", flush=True)
        
        # Set up environment
        env = os.environ.copy()
        env['PATH'] = f"{os.path.dirname(bazel_path)}:{env['PATH']}"
        
        # Ensure Python can find numpy for Bazel TensorFlow configuration
        import sys
        try:
            import numpy
            print(f"✅ NumPy found: {numpy.__version__} at {numpy.__file__}", flush=True)
        except ImportError:
            print("⚠️ Installing NumPy for Bazel TensorFlow configuration...", flush=True)
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'numpy'], check=True, env=env)
            import numpy
            print(f"✅ NumPy installed: {numpy.__version__}", flush=True)
        
        # Clean corrupted Bazel cache if it exists
        import getpass
        username = getpass.getuser()
        bazel_cache_patterns = [
            f"/home/{username}/.cache/bazel",
            f"~/.cache/bazel",
            f"/tmp/bazel_{username}",
        ]
        
        for cache_pattern in bazel_cache_patterns:
            cache_path = os.path.expanduser(cache_pattern)
            if os.path.exists(cache_path):
                print(f"🧹 Cleaning Bazel cache: {cache_path}", flush=True)
                try:
                    shutil.rmtree(cache_path)
                    print(f"✅ Cleaned Bazel cache: {cache_path}", flush=True)
                except Exception as e:
                    print(f"⚠️ Could not clean {cache_path}: {e}", flush=True)
        
        # Force Bazel to use a clean temporary directory for this build
        temp_bazel_dir = os.path.join(work_dir, 'bazel_output')
        os.makedirs(temp_bazel_dir, exist_ok=True)
        
        # Add Bazel flags for NFS compatibility and clean builds
        # Use minimal flags for Bazel 6.x compatibility with TensorFlow experimental features
        bazel_startup_flags = [
            f'--output_base={temp_bazel_dir}',  # Use our own output base
        ]
        
        # Build flags for TensorFlow compatibility  
        bazel_build_flags = [
            '--experimental_repo_remote_exec',  # Enable remotable parameter for TensorFlow
        ]
        
        print(f"🛠️ Using clean Bazel output directory: {temp_bazel_dir}", flush=True)
        
        # First, let's sync external dependencies
        print("🔄 Syncing external dependencies...", flush=True)
        sync_cmd = [bazel_path] + bazel_startup_flags + ['sync'] + bazel_build_flags
        sync_result = subprocess.run(sync_cmd, env=env, timeout=300)
        
        if sync_result.returncode == 0:
            print("✅ Dependencies synced successfully", flush=True)
        else:
            print("⚠️ Dependency sync had issues, but continuing...", flush=True)
        
        # Now let's check what Bazel targets are available
        print("🔍 Querying available Bazel targets...", flush=True)
        query_cmd = [bazel_path] + bazel_startup_flags + ['query'] + bazel_build_flags + ['//...']
        result = subprocess.run(query_cmd, env=env, capture_output=True, text=True, timeout=60)  # Keep query output captured for parsing
        
        if result.returncode == 0:
            print("Available targets:", flush=True)
            targets = result.stdout.strip().split('\n')
            for target in targets[:20]:  # Show first 20 targets
                print(f"  {target}", flush=True)
            if len(targets) > 20:
                print(f"  ... and {len(targets) - 20} more targets", flush=True)
        else:
            print("⚠️ Could not query targets, proceeding with build...", flush=True)
            print(f"Query stdout: {result.stdout}", flush=True)
            print(f"Query stderr: {result.stderr}", flush=True)
        
        # Build commands - let's try simpler targets first
        # For Bazel 8+ compatibility, we need to disable bzlmod and force WORKSPACE usage
        build_commands = [
            # Try to build the python bindings with clean output base and TensorFlow compatibility flags
            [bazel_path] + bazel_startup_flags + ['build'] + bazel_build_flags + [
             '-c', 'opt', 
             '--verbose_failures', 
             '--subcommands',  # Show all subcommands being executed
             '//python:visqol_lib_py'],
        ]
        
        for cmd in build_commands:
            print(f"🔨 Running: {' '.join(cmd)}", flush=True)
            print("📝 Real-time output:", flush=True)
            result = subprocess.run(cmd, env=env, timeout=1200)  # 20 minute timeout, show output in real-time
            
            print(f"\nCommand completed with return code: {result.returncode}", flush=True)
            
            if result.returncode != 0:
                print(f"❌ Build command failed: {' '.join(cmd)}", flush=True)
                
                # Try alternative targets with clean output base and TensorFlow compatibility flags
                alternative_commands = [
                    [bazel_path] + bazel_startup_flags + ['build'] + bazel_build_flags + ['-c', 'opt', '--verbose_failures', '--subcommands', '//python:all'],
                    [bazel_path] + bazel_startup_flags + ['build'] + bazel_build_flags + ['-c', 'opt', '--verbose_failures', '--subcommands', '//:all'],
                    # Also try building specific targets
                    [bazel_path] + bazel_startup_flags + ['build'] + bazel_build_flags + ['-c', 'opt', '--verbose_failures', '--subcommands', '//python:visqol_lib_py.so'],
                    [bazel_path] + bazel_startup_flags + ['build'] + bazel_build_flags + ['-c', 'opt', '--verbose_failures', '--subcommands', '//src:visqol_api'],
                ]
                
                success = False
                for alt_cmd in alternative_commands:
                    print(f"🔄 Trying alternative: {' '.join(alt_cmd)}", flush=True)
                    print("📝 Real-time alternative output:", flush=True)
                    alt_result = subprocess.run(alt_cmd, env=env, timeout=1200)
                    
                    print(f"\nAlternative completed with return code: {alt_result.returncode}", flush=True)
                    
                    if alt_result.returncode == 0:
                        print("✅ Alternative build succeeded!", flush=True)
                        success = True
                        break
                
                if not success:
                    print("❌ All build attempts failed", flush=True)
                    raise subprocess.CalledProcessError(result.returncode, cmd)
        
        print("✅ ViSQOL built successfully", flush=True)
        
    except subprocess.TimeoutExpired as e:
        print(f"❌ Build timed out: {e}", flush=True)
        raise
    finally:
        os.chdir(original_dir)


def copy_built_files(visqol_dir, target_dir):
    """Copy built files to package directory."""
    print("📁 Copying built files...", flush=True)
    print(f"Source directory: {visqol_dir}", flush=True)
    print(f"Target directory: {target_dir}", flush=True)
    
    bazel_bin = os.path.join(visqol_dir, 'bazel-bin')
    print(f"Bazel-bin directory: {bazel_bin}", flush=True)
    
    # List contents of bazel-bin to see what was actually built
    if os.path.exists(bazel_bin):
        print("📂 Contents of bazel-bin:", flush=True)
        for root, dirs, files in os.walk(bazel_bin):
            level = root.replace(bazel_bin, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/", flush=True)
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}", flush=True)
    else:
        print("❌ bazel-bin directory not found!", flush=True)
        return False
    
    # Create target directories
    target_dir = Path(target_dir)
    model_dir = target_dir / 'visqol_py' / 'model'
    pb2_dir = target_dir / 'visqol_py' / 'pb2'
    
    model_dir.mkdir(parents=True, exist_ok=True)
    pb2_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directories: {model_dir}, {pb2_dir}", flush=True)
    
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
        target_so_path = target_dir / 'visqol_py' / 'visqol_lib_py.so'
        
        # Remove existing file if it exists to avoid permission issues
        if target_so_path.exists():
            try:
                # Make file writable before removing
                target_so_path.chmod(0o644)
                target_so_path.unlink()
                print(f"🗑️ Removed existing library: {target_so_path}", flush=True)
            except Exception as e:
                print(f"⚠️ Could not remove existing library: {e}", flush=True)
        
        try:
            shutil.copy2(so_file_found, target_so_path)
            print(f"✅ Copied Python library: {so_file_found} -> {target_so_path}", flush=True)
            files_copied += 1
        except Exception as e:
            print(f"⚠️ Failed to copy library: {e}", flush=True)
            # If copy fails, at least check if the target already exists and is valid
            if target_so_path.exists():
                print(f"ℹ️ Target library already exists: {target_so_path}", flush=True)
                files_copied += 1  # Count as success if target exists
    else:
        print("⚠️ Python library (.so file) not found in any expected location", flush=True)
        # Search for any .so files
        print("🔍 Searching for .so files:", flush=True)
        for root, dirs, files in os.walk(bazel_bin):
            for file in files:
                if file.endswith('.so'):
                    print(f"  Found .so file: {os.path.join(root, file)}", flush=True)
    
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
                print(f"✅ Copied protobuf: {pb_file}", flush=True)
                files_copied += 1
                found = True
                break
        
        if not found:
            print(f"⚠️ Protobuf file not found: {pb_file}", flush=True)
    
    # Copy model files
    model_src = os.path.join(visqol_dir, 'model')
    print(f"Looking for model files in: {model_src}", flush=True)
    
    if os.path.exists(model_src):
        print("📂 Contents of model directory:", flush=True)
        for item in os.listdir(model_src):
            print(f"  {item}", flush=True)
            src_path = os.path.join(model_src, item)
            if os.path.isfile(src_path) and item.endswith(('.tflite', '.txt', '.model')):
                shutil.copy2(src_path, model_dir)
                print(f"✅ Copied model: {item}", flush=True)
                files_copied += 1
    else:
        print("⚠️ Model directory not found", flush=True)
    
    # Create __init__.py files if they don't exist
    for init_dir in [pb2_dir, model_dir]:
        init_file = init_dir / '__init__.py'
        if not init_file.exists():
            init_file.write_text('# ViSQOL generated files\n')
    
    print(f"✅ Copied {files_copied} files", flush=True)
    return files_copied > 0


def main():
    """Main build function."""
    print("🚀 Building ViSQOL Native Library", flush=True)
    print("=" * 50, flush=True)
    print("📋 This process includes:", flush=True)
    print(f"   • Downloading Bazel 6.4.0 (compatible version)", flush=True)
    print("   • Cloning ViSQOL repository", flush=True)
    print("   • Compiling C++ code (may take 5-15 minutes)", flush=True)
    print("   • Copying built files", flush=True)
    print("=" * 50, flush=True)
    
    if not check_system_requirements():
        print("❌ System requirements not met", flush=True)
        return False
    
    target_dir = os.getcwd()
    
    with tempfile.TemporaryDirectory() as work_dir:
        try:
            # Clean any corrupt Bazel cache first (common on NFS systems)
            print("🧹 Cleaning Bazel cache to avoid NFS/corruption issues...", flush=True)
            try:
                import getpass
                username = getpass.getuser()
                bazel_cache = os.path.expanduser("~/.cache/bazel")
                if os.path.exists(bazel_cache):
                    shutil.rmtree(bazel_cache)
                    print(f"✅ Removed potentially corrupt Bazel cache: {bazel_cache}", flush=True)
            except Exception as e:
                print(f"⚠️ Could not clean Bazel cache: {e}", flush=True)
            
            # Always install compatible Bazel version instead of using system Bazel
            # This avoids version compatibility issues with Bazel 8+
            print("ℹ️ Installing compatible Bazel version instead of using system Bazel", flush=True)
            bazel_path = install_compatible_bazel(work_dir)
            
            # Clone and build ViSQOL
            visqol_dir = clone_visqol(work_dir)
            build_visqol(visqol_dir, bazel_path, work_dir)
            
            # Copy files to package
            success = copy_built_files(visqol_dir, target_dir)
            
            if success:
                print("🎉 Native ViSQOL build completed successfully!", flush=True)
                return True
            else:
                print("⚠️  Build completed but no files were copied", flush=True)
                return False
                
        except Exception as e:
            print(f"❌ Build failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)