#!/usr/bin/env python3
"""
Test script to demonstrate the ML flags in the help system.
"""

import subprocess
import sys
import os

def test_help_output():
    """Test the help output to show ML flags."""
    
    # Get the path to main.py
    main_py_path = os.path.join(os.path.dirname(__file__), "main.py")
    
    if not os.path.exists(main_py_path):
        print(f"❌ Error: main.py not found at {main_py_path}")
        return
    
    print("🤖 Testing ML Flags in Help System")
    print("=" * 50)
    
    # Test 1: Show basic help
    print("\n1️⃣ Basic Help (should show ML flags in argument parser):")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            sys.executable, main_py_path, "--help"
        ], capture_output=True, text=True, timeout=10)
        
        # Look for ML-related flags in the output
        help_output = result.stdout
        ml_flags = [
            "--enable-ml-selection",
            "--ml-learning", 
            "--ml-ensemble-method",
            "--ml-confidence-threshold",
            "--ml-analytics",
            "--ml-retrain",
            "--ml-cleanup"
        ]
        
        print("ML Flags found in help:")
        for flag in ml_flags:
            if flag in help_output:
                print(f"  ✅ {flag}")
            else:
                print(f"  ❌ {flag} - Not found")
        
        # Show a snippet of the help output
        print(f"\nHelp output snippet (first 20 lines):")
        lines = help_output.split('\n')[:20]
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line}")
        
        if len(help_output.split('\n')) > 20:
            print("... (truncated)")
            
    except subprocess.TimeoutExpired:
        print("❌ Help command timed out")
    except Exception as e:
        print(f"❌ Error running help command: {e}")
    
    # Test 2: Show help examples (should show ML section)
    print("\n2️⃣ Help Examples (should show ML section):")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            sys.executable, main_py_path, "--help", "all"
        ], capture_output=True, text=True, timeout=15)
        
        help_output = result.stdout
        
        # Look for ML section in examples
        if "[ML] MACHINE LEARNING MODEL SELECTION:" in help_output:
            print("✅ ML section found in help examples")
            
            # Extract ML section
            lines = help_output.split('\n')
            ml_section_start = None
            ml_section_end = None
            
            for i, line in enumerate(lines):
                if "[ML] MACHINE LEARNING MODEL SELECTION:" in line:
                    ml_section_start = i
                elif ml_section_start is not None and line.startswith('[') and line != lines[ml_section_start]:
                    ml_section_end = i
                    break
            
            if ml_section_start is not None:
                ml_section_end = ml_section_end or len(lines)
                ml_section = lines[ml_section_start:ml_section_end]
                
                print("\nML Section from help examples:")
                for line in ml_section:
                    print(f"  {line}")
        else:
            print("❌ ML section not found in help examples")
            
    except subprocess.TimeoutExpired:
        print("❌ Help examples command timed out")
    except Exception as e:
        print(f"❌ Error running help examples command: {e}")
    
    # Test 3: Show system info (should show ML module)
    print("\n3️⃣ System Info (should show ML module):")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            sys.executable, main_py_path
        ], capture_output=True, text=True, timeout=10)
        
        help_output = result.stdout
        
        if "🧠 ML Model Selection" in help_output:
            print("✅ ML module found in system info")
            
            # Show the modules section
            lines = help_output.split('\n')
            for line in lines:
                if "Available modules:" in line or line.startswith("  🧠") or line.startswith("  🔍") or line.startswith("  🛡️") or line.startswith("  📊") or line.startswith("  🤖"):
                    print(f"  {line}")
        else:
            print("❌ ML module not found in system info")
            
    except subprocess.TimeoutExpired:
        print("❌ System info command timed out")
    except Exception as e:
        print(f"❌ Error running system info command: {e}")
    
    print("\n🎉 ML Help System Test Complete!")
    print("\n💡 To see the full help with ML flags:")
    print("   python main.py --help")
    print("\n💡 To see ML examples:")
    print("   python main.py --help all")

if __name__ == "__main__":
    test_help_output()
