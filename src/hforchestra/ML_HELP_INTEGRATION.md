# ML Flags Integration in Help System

## Overview

The ML-based model selection flags have been successfully integrated into the HFOrchestra help system. Users can now discover and learn about ML capabilities through the built-in help commands.

## What Was Added

### 1. **Basic Usage Section**
Added ML selection to the basic usage examples:

```bash
[OUTPUT] BASIC USAGE:
  python main.py --prompt "Your prompt here"
  python main.py --file "ANY_FILE" --prompt "What is this about?"
  python main.py --enable-ml-selection --prompt "Use ML-enhanced model selection"  # NEW
```

### 2. **Comprehensive ML Section**
Added a dedicated ML section with detailed examples:

```bash
[ML] MACHINE LEARNING MODEL SELECTION:
  # Basic ML-enhanced selection
  python main.py --enable-ml-selection --selection-strategy ml_enhanced --prompt "Write a story"
  
  # ML selection with learning enabled
  python main.py --enable-ml-selection --ml-learning --prompt "Classify this sentiment"
  
  # Ensemble methods for robust selection
  python main.py --enable-ml-selection --ml-ensemble-method voting --selection-strategy ml_voting --prompt "Summarize text"
  python main.py --enable-ml-selection --ml-ensemble-method consensus --selection-strategy ml_consensus --prompt "Translate this"
  
  # High confidence selection
  python main.py --enable-ml-selection --ml-confidence-threshold 0.8 --prompt "Analyze this data"
  
  # ML analytics and management
  python main.py --ml-analytics                    # Show ML performance statistics
  python main.py --ml-retrain                     # Force model retraining
  python main.py --ml-cleanup 30                  # Clean up old training data
  
  # Advanced ML configuration
  python main.py --enable-ml-selection --ml-learning --ml-ensemble-method adaptive --selection-strategy ml_adaptive --prompt "Complex analysis"
```

### 3. **System Information**
Added ML module to the available modules list:

```bash
Available modules:
  🔍 Model Discovery - Find and evaluate HuggingFace models
  🛡️ Security - ATLAS threat detection and monitoring
  📊 Performance - System monitoring and optimization
  🔍 PE Analysis - Malware detection and binary analysis
  🤖 Orchestration - Multi-provider LLM management
  🧠 ML Model Selection - Machine learning-based intelligent model selection  # NEW
```

## How to Access ML Help

### 1. **Basic Help** (Shows All Flags)
```bash
python main.py --help
```
This shows all available flags including the new ML flags:
- `--enable-ml-selection`
- `--ml-learning`
- `--ml-ensemble-method`
- `--ml-confidence-threshold`
- `--ml-fallback`
- `--ml-analytics`
- `--ml-retrain`
- `--ml-cleanup`

### 2. **Comprehensive Examples**
```bash
python main.py --help all
```
This shows the detailed ML section with practical examples.

### 3. **System Information**
```bash
python main.py
```
This shows the ML module in the available modules list.

### 4. **Search Help by Keyword**
```bash
python main.py --help ml
```
This searches for ML-related flags and examples.

## ML Flags Documentation

### Core ML Flags
- **`--enable-ml-selection`**: Enable ML-based model selection system
- **`--ml-learning`**: Enable learning from task execution results
- **`--ml-ensemble-method`**: Choose ensemble method (voting, consensus, etc.)
- **`--ml-confidence-threshold`**: Set minimum confidence threshold (0.0-1.0)
- **`--ml-fallback`**: Enable fallback to enhanced selector (default: True)

### ML Management Flags
- **`--ml-analytics`**: Show ML performance statistics and analytics
- **`--ml-retrain`**: Force retraining of ML models with current data
- **`--ml-cleanup DAYS`**: Clean up old training data (e.g., `--ml-cleanup 30`)

### Enhanced Selection Strategies
- **`--selection-strategy ml_enhanced`**: ML-enhanced selection (recommended)
- **`--selection-strategy ml_ensemble`**: Ensemble-based selection
- **`--selection-strategy ml_voting`**: Voting ensemble method
- **`--selection-strategy ml_consensus`**: Consensus-based selection
- **`--selection-strategy ml_stacking`**: Stacking ensemble method
- **`--selection-strategy ml_adaptive`**: Adaptive ensemble method

## Example Usage from Help

### Basic ML Selection
```bash
python main.py --enable-ml-selection --prompt "Write a story about AI"
```

### Learning-Enabled Selection
```bash
python main.py --enable-ml-selection --ml-learning --prompt "Classify this sentiment"
```

### Ensemble Methods
```bash
python main.py --enable-ml-selection --ml-ensemble-method voting --selection-strategy ml_voting --prompt "Summarize text"
```

### High Confidence Selection
```bash
python main.py --enable-ml-selection --ml-confidence-threshold 0.8 --prompt "Analyze this data"
```

### ML Analytics
```bash
python main.py --ml-analytics
```

### Force Retraining
```bash
python main.py --ml-retrain
```

### Clean Up Old Data
```bash
python main.py --ml-cleanup 30
```

## Benefits of Help Integration

1. **Discoverability**: Users can easily find ML capabilities through help commands
2. **Learning**: Comprehensive examples show how to use ML features effectively
3. **Reference**: Quick access to all ML flags and their descriptions
4. **Integration**: ML flags are seamlessly integrated with existing help system
5. **Consistency**: Follows the same help format as other HFOrchestra features

## Testing the Help Integration

Run the test script to verify ML flags appear in help:

```bash
python test_ml_help.py
```

This will test:
- Basic help output for ML flags
- Help examples showing ML section
- System info showing ML module

## Future Enhancements

The help system can be extended with:
- Interactive ML tutorials
- Performance benchmarks
- Best practices guide
- Troubleshooting section
- Advanced configuration examples

---

**The ML flags are now fully integrated into the HFOrchestra help system, making them easily discoverable and accessible to all users! 🚀**
