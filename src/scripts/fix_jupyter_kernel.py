#!/usr/bin/env python3
"""
Jupyter Kernel Management and Recovery Script
Fixes common kernel issues and provides better kernel management
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path

def run_command(cmd, capture_output=True, timeout=30):
    """Run a command with error handling"""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, timeout=timeout)
        return result
    except subprocess.TimeoutExpired:
        print(f"⚠️ Command timed out: {' '.join(cmd)}")
        return None
    except Exception as e:
        print(f"❌ Command failed: {' '.join(cmd)} - {e}")
        return None

def list_kernels():
    """List all available kernels"""
    print("🔍 Listing available kernels...")
    result = run_command([sys.executable, "-m", "jupyter", "kernelspec", "list"])
    if result and result.returncode == 0:
        print(result.stdout)
    else:
        print("❌ Failed to list kernels")

def kill_all_kernels():
    """Kill all running kernels"""
    print("🔄 Killing all running kernels...")
    
    # Try to stop all kernels
    result = run_command([sys.executable, "-m", "jupyter", "notebook", "stop"], timeout=10)
    if result and result.returncode == 0:
        print("✅ Successfully stopped notebook server")
    
    # Try alternative methods
    try:
        # Kill jupyter processes
        if os.name == 'nt':  # Windows
            run_command(["taskkill", "/f", "/im", "jupyter.exe"], timeout=5)
            run_command(["taskkill", "/f", "/im", "python.exe"], timeout=5)
        else:  # Unix/Linux/Mac
            run_command(["pkill", "-f", "jupyter"], timeout=5)
    except:
        pass

def install_kernel():
    """Install/Reinstall the Python kernel"""
    print("🔧 Installing Python kernel...")
    
    # Remove existing kernel if it exists
    try:
        run_command([sys.executable, "-m", "jupyter", "kernelspec", "remove", "python3", "-f"], timeout=10)
    except:
        pass
    
    # Install new kernel
    result = run_command([sys.executable, "-m", "ipykernel", "install", "--user", "--name=python3", "--display-name=Python 3"], timeout=30)
    if result and result.returncode == 0:
        print("✅ Python kernel installed successfully")
    else:
        print("❌ Failed to install kernel")

def start_notebook_with_kernel_management(notebook_path=None):
    """Start Jupyter notebook with kernel management"""
    print("🚀 Starting Jupyter with kernel management...")
    
    # Kill existing processes
    kill_all_kernels()
    
    # Wait a moment
    time.sleep(2)
    
    # Install kernel if needed
    install_kernel()
    
    # Start notebook with specific settings
    cmd = [
        sys.executable, "-m", "notebook",
        "--no-browser",
        "--allow-root",
        "--ip=127.0.0.1",
        "--port=8888",
        "--NotebookApp.token=''",
        "--NotebookApp.password=''",
        "--NotebookApp.allow_origin='*'",
        "--NotebookApp.allow_remote_access=True",
        "--NotebookApp.kernel_manager_class='jupyter_server.services.kernels.kernelmanager.AsyncMappingKernelManager'"
    ]
    
    if notebook_path:
        cmd.append(str(Path(notebook_path).resolve()))
    
    print(f"📝 Starting with command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Jupyter: {e}")
        print("🔄 Trying alternative method...")
        
        # Try jupyter lab as alternative
        try:
            alt_cmd = [sys.executable, "-m", "jupyter", "lab", "--no-browser"]
            if notebook_path:
                alt_cmd.append(str(Path(notebook_path).resolve()))
            subprocess.run(alt_cmd, check=True)
        except:
            print("❌ Both methods failed. Please manually start Jupyter:")
            print("   jupyter notebook --no-browser")
            if notebook_path:
                print(f"   Or open: {notebook_path}")

def fix_kernel_issues():
    """Main function to fix kernel issues"""
    print("🔧 Jupyter Kernel Fix Tool")
    print("=" * 40)
    
    # List current kernels
    list_kernels()
    
    # Kill all kernels
    kill_all_kernels()
    
    # Install fresh kernel
    install_kernel()
    
    # List kernels again
    list_kernels()
    
    print("✅ Kernel fix completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "fix":
            fix_kernel_issues()
        elif sys.argv[1] == "start":
            notebook_path = sys.argv[2] if len(sys.argv) > 2 else None
            start_notebook_with_kernel_management(notebook_path)
        elif sys.argv[1] == "list":
            list_kernels()
        elif sys.argv[1] == "kill":
            kill_all_kernels()
        else:
            print("Usage:")
            print("  python fix_jupyter_kernel.py fix     - Fix kernel issues")
            print("  python fix_jupyter_kernel.py start   - Start Jupyter with kernel management")
            print("  python fix_jupyter_kernel.py start <notebook> - Start with specific notebook")
            print("  python fix_jupyter_kernel.py list    - List kernels")
            print("  python fix_jupyter_kernel.py kill    - Kill all kernels")
    else:
        fix_kernel_issues()
