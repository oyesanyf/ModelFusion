#!/usr/bin/env python3
"""
Installation script for HuggingFace Orchestrator dependencies.
"""

import subprocess
import sys
import importlib

def check_module(module_name):
    """Check if a module is installed."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🚀 HuggingFace Orchestrator - Dependency Installer")
    print("=" * 50)
    
    # Core dependencies that are required
    core_dependencies = [
        "aiohttp",
        "requests", 
        "transformers",
        "torch",
        "Pillow",
        "numpy",
        "pandas"
    ]
    
    # Optional dependencies
    optional_dependencies = [
        "opencv-python",
        "librosa",
        "magika",
        "openai",
        "anthropic",
        "google-generativeai"
    ]
    
    print("\n📦 Checking core dependencies...")
    missing_core = []
    for dep in core_dependencies:
        if check_module(dep):
            print(f"✅ {dep} - Installed")
        else:
            print(f"❌ {dep} - Missing")
            missing_core.append(dep)
    
    print("\n📦 Checking optional dependencies...")
    missing_optional = []
    for dep in optional_dependencies:
        if check_module(dep):
            print(f"✅ {dep} - Installed")
        else:
            print(f"⚠️  {dep} - Missing (optional)")
            missing_optional.append(dep)
    
    # Install missing core dependencies
    if missing_core:
        print(f"\n🔧 Installing missing core dependencies: {', '.join(missing_core)}")
        for dep in missing_core:
            print(f"Installing {dep}...")
            if install_package(dep):
                print(f"✅ Successfully installed {dep}")
            else:
                print(f"❌ Failed to install {dep}")
                return False
    else:
        print("\n✅ All core dependencies are installed!")
    
    # Offer to install optional dependencies
    if missing_optional:
        print(f"\n📋 Optional dependencies available: {', '.join(missing_optional)}")
        response = input("Would you like to install optional dependencies? (y/n): ").lower()
        if response in ['y', 'yes']:
            print("Installing optional dependencies...")
            for dep in missing_optional:
                print(f"Installing {dep}...")
                if install_package(dep):
                    print(f"✅ Successfully installed {dep}")
                else:
                    print(f"⚠️  Failed to install {dep} (optional)")
    
    print("\n🎉 Installation complete!")
    print("\n💡 Next steps:")
    print("  1. Set up your API keys (optional):")
    print("     • OPENAI_API_KEY")
    print("     • ANTHROPIC_API_KEY") 
    print("     • GOOGLE_GEMINI_API_KEY")
    print("  2. Run the orchestrator:")
    print("     • python HuggingFace_orhcestrator.py --help")
    print("     • python HuggingFace_orhcestrator.py --visual-question-answering --file 'image.jpg' --prompt 'What is in this image?'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 