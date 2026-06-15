#!/usr/bin/env python3
"""
Example usage of ML-based model selection flags in HFOrchestra.

This script demonstrates how to use the new ML flags with your HFOrchestra system.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and display the result."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"💻 Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error running command: {e}")

def main():
    """Demonstrate ML flag usage."""
    
    print("🤖 HFOrchestra ML-Based Model Selection - Flag Usage Examples")
    print("=" * 70)
    
    # Get the path to main.py
    main_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
    
    if not os.path.exists(main_py_path):
        print(f"❌ Error: main.py not found at {main_py_path}")
        print("Please run this script from the examples directory")
        return
    
    # Example 1: Enable ML selection with basic task
    run_command([
        sys.executable, main_py_path,
        "--enable-ml-selection",
        "--selection-strategy", "ml_enhanced",
        "--prompt", "Write a short story about AI"
    ], "Basic ML-enhanced model selection")
    
    # Example 2: Use ensemble voting method
    run_command([
        sys.executable, main_py_path,
        "--enable-ml-selection",
        "--ml-ensemble-method", "voting",
        "--selection-strategy", "ml_voting",
        "--prompt", "Classify this sentiment: I love this product!"
    ], "ML ensemble voting method")
    
    # Example 3: Enable learning and show analytics
    run_command([
        sys.executable, main_py_path,
        "--enable-ml-selection",
        "--ml-learning",
        "--selection-strategy", "ml_consensus",
        "--prompt", "Summarize this text: Machine learning is fascinating."
    ], "ML selection with learning enabled")
    
    # Example 4: Show ML analytics
    run_command([
        sys.executable, main_py_path,
        "--ml-analytics"
    ], "Display ML selection analytics")
    
    # Example 5: Force model retraining
    run_command([
        sys.executable, main_py_path,
        "--ml-retrain"
    ], "Force ML model retraining")
    
    # Example 6: Clean up old training data
    run_command([
        sys.executable, main_py_path,
        "--ml-cleanup", "30"
    ], "Clean up ML training data older than 30 days")
    
    # Example 7: Advanced ML configuration
    run_command([
        sys.executable, main_py_path,
        "--enable-ml-selection",
        "--ml-learning",
        "--ml-ensemble-method", "adaptive",
        "--ml-confidence-threshold", "0.8",
        "--selection-strategy", "ml_adaptive",
        "--prompt", "Translate this to Spanish: Hello, how are you?"
    ], "Advanced ML configuration with high confidence threshold")
    
    # Example 8: Show help for ML flags
    run_command([
        sys.executable, main_py_path,
        "--help"
    ], "Show help including ML flags")
    
    print(f"\n{'='*70}")
    print("🎉 ML Flag Usage Examples Complete!")
    print("\n💡 Key ML Flags Summary:")
    print("  --enable-ml-selection     : Enable ML-based model selection")
    print("  --ml-learning            : Enable learning from task results")
    print("  --ml-ensemble-method     : Choose ensemble method (voting, consensus, etc.)")
    print("  --ml-confidence-threshold: Set minimum confidence (0.0-1.0)")
    print("  --ml-analytics           : Show ML performance analytics")
    print("  --ml-retrain             : Force model retraining")
    print("  --ml-cleanup DAYS        : Clean up old training data")
    print("\n🎯 ML Selection Strategies:")
    print("  --selection-strategy ml_enhanced  : ML-enhanced selection")
    print("  --selection-strategy ml_ensemble  : Ensemble-based selection")
    print("  --selection-strategy ml_voting    : Voting ensemble")
    print("  --selection-strategy ml_consensus : Consensus ensemble")
    print("  --selection-strategy ml_stacking  : Stacking ensemble")
    print("  --selection-strategy ml_adaptive  : Adaptive ensemble")
    print("\n🚀 The ML system learns from your usage patterns and improves over time!")

if __name__ == "__main__":
    main()
