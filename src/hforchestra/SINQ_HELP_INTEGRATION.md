# SINQ Quantization Integration in Help System

## Overview

The SINQ (Sinkhorn-Normalized Quantization) integration has been successfully added to the HFOrchestra help system. Users can now discover and learn about SINQ quantization capabilities through the built-in help commands.

## What Was Added

### 1. **Basic Usage Section**
Added SINQ to the basic usage examples:

```bash
[OUTPUT] BASIC USAGE:
  python main.py --prompt "Your prompt here"
  python main.py --file "ANY_FILE" --prompt "What is this about?"
  python main.py --enable-ml-selection --prompt "Use ML-enhanced model selection"
  python main.py --sinq --prompt "Use quantized models for memory efficiency"  # NEW
```

### 2. **Comprehensive SINQ Section**
Added a dedicated SINQ section with detailed examples:

```bash
[SINQ] MODEL QUANTIZATION:
  # Basic SINQ quantization (reduces memory usage while preserving accuracy)
  python main.py --sinq --prompt "Generate a story"
  
  # SINQ with custom bit-width (4-bit quantization)
  python main.py --sinq --sinq-nbits 4 --prompt "Classify this text"
  
  # SINQ with different group size and tiling mode
  python main.py --sinq --sinq-group-size 128 --sinq-tiling-mode 2D --prompt "Summarize this article"
  
  # SINQ with calibrated method (A-SINQ)
  python main.py --sinq --sinq-method asinq --prompt "Translate to Spanish"
  
  # SINQ with all custom parameters
  python main.py --sinq --sinq-nbits 3 --sinq-group-size 64 --sinq-tiling-mode 1D --sinq-method sinq --prompt "Analyze sentiment"
```

### 3. **System Information**
Added SINQ module to the available modules list:

```bash
Available modules:
  🔍 Model Discovery - Find and evaluate HuggingFace models
  🛡️ Security - ATLAS threat detection and monitoring
  📊 Performance - System monitoring and optimization
  🔍 PE Analysis - Malware detection and binary analysis
  🤖 Orchestration - Multi-provider LLM management
  🧠 ML Model Selection - Machine learning-based intelligent model selection
  🔧 SINQ Quantization - Model quantization for memory efficiency  # NEW
```

### 4. **Global Options Documentation**
Added SINQ flags to the global options section:

```bash
[TOOL] GLOBAL OPTIONS:
  --sinq                   Enable SINQ quantization for best selected models
  --sinq-nbits BITS        SINQ quantization bit-width (2,3,4,5,6,8, default: 4)
  --sinq-group-size SIZE   SINQ quantization group size (64,128, default: 64)
  --sinq-tiling-mode MODE  SINQ tiling strategy (1D,2D, default: 1D)
  --sinq-method METHOD     SINQ quantization method (sinq,asinq, default: sinq)
```

### 5. **Combining Options Examples**
Added SINQ examples to the combining options section:

```bash
[BULB] COMBINING OPTIONS:
  python main.py --sinq --sinq-nbits 4 --verbose --text-generation --prompt "Write a creative story"
  python main.py --sinq --enable-ml --selection-strategy multi_objective --prompt "Analyze this data"
```

### 6. **Contextual Help Examples**
Added SINQ flag examples to the contextual help system:

```bash
--sinq: 'python main.py --sinq --prompt "Generate a story"\n  python main.py --sinq --sinq-nbits 4 --prompt "Classify this text"'
--sinq-nbits: 'python main.py --sinq --sinq-nbits 4 --prompt "Classify this text"\n  python main.py --sinq --sinq-nbits 3 --prompt "Summarize this article"'
--sinq-group-size: 'python main.py --sinq --sinq-group-size 128 --prompt "Analyze sentiment"\n  python main.py --sinq --sinq-group-size 64 --prompt "Translate text"'
--sinq-tiling-mode: 'python main.py --sinq --sinq-tiling-mode 2D --prompt "Generate content"\n  python main.py --sinq --sinq-tiling-mode 1D --prompt "Classify text"'
--sinq-method: 'python main.py --sinq --sinq-method sinq --prompt "Generate text"\n  python main.py --sinq --sinq-method asinq --prompt "Analyze data"'
```

## How to Access SINQ Help

### 1. **Basic Help** (Shows All Flags)
```bash
python main.py --help
```
This shows all available flags including the new SINQ flags:
- `--sinq`
- `--sinq-nbits`
- `--sinq-group-size`
- `--sinq-tiling-mode`
- `--sinq-method`

### 2. **Comprehensive Examples**
```bash
python main.py --help all
```
This shows the detailed SINQ section with practical examples.

### 3. **System Information**
```bash
python main.py
```
This shows the SINQ module in the available modules list.

### 4. **Search Help by Keyword**
```bash
python main.py --help sinq
```
This searches for SINQ-related flags and examples.

### 5. **Contextual Help for Specific Flags**
```bash
python main.py --help --sinq
python main.py --help --sinq-nbits
python main.py --help --sinq-method
```

## SINQ Flags Documentation

### Core SINQ Flags
- **`--sinq`**: Enable SINQ quantization for best selected models
- **`--sinq-nbits`**: Set quantization bit-width (2,3,4,5,6,8, default: 4)
- **`--sinq-group-size`**: Set quantization group size (64,128, default: 64)
- **`--sinq-tiling-mode`**: Set tiling strategy (1D,2D, default: 1D)
- **`--sinq-method`**: Set quantization method (sinq,asinq, default: sinq)

### SINQ Configuration Options

#### Bit-width Options (--sinq-nbits)
- **2-bit**: Maximum compression, may have quality loss
- **3-bit**: High compression with good quality
- **4-bit**: Balanced compression and quality (recommended)
- **5-bit**: Lower compression, higher quality
- **6-bit**: Minimal compression, high quality
- **8-bit**: Minimal compression, maximum quality

#### Group Size Options (--sinq-group-size)
- **64**: Smaller groups, more precise quantization
- **128**: Larger groups, faster quantization

#### Tiling Mode Options (--sinq-tiling-mode)
- **1D**: One-dimensional tiling (recommended for most cases)
- **2D**: Two-dimensional tiling (may provide better quality for some models)

#### Method Options (--sinq-method)
- **sinq**: Calibration-free quantization (faster, good quality)
- **asinq**: Calibrated quantization (slower, potentially better quality)

## Usage Examples

### Basic Quantization
```bash
# Enable SINQ with default settings
python main.py --sinq --prompt "Generate a story"
```

### Custom Configuration
```bash
# 4-bit quantization with 128 group size
python main.py --sinq --sinq-nbits 4 --sinq-group-size 128 --prompt "Classify this text"

# 2D tiling with calibrated method
python main.py --sinq --sinq-tiling-mode 2D --sinq-method asinq --prompt "Summarize this article"
```

### Combined with Other Features
```bash
# SINQ with ML selection
python main.py --sinq --enable-ml --selection-strategy multi_objective --prompt "Analyze this data"

# SINQ with verbose output
python main.py --sinq --sinq-nbits 4 --verbose --text-generation --prompt "Write a creative story"
```

## Benefits of SINQ Quantization

- **Memory Efficiency**: Reduces model memory usage by 2-4x depending on bit-width
- **Speed**: SINQ quantizes models ~2x faster than HQQ and ~4x faster than AWQ
- **Quality**: Maintains high model quality with minimal accuracy loss
- **Flexibility**: Supports both calibration-free (SINQ) and calibrated (A-SINQ) methods
- **Integration**: Seamlessly integrates with existing model selection workflow

## Installation Requirements

To use SINQ, install it from the GitHub repository:
```bash
pip install git+https://github.com/huawei-csl/SINQ.git
```

The integration gracefully handles cases where SINQ is not installed, providing helpful error messages and falling back to normal operation.

## Testing

SINQ flags are included in the comprehensive flag testing suite:
```bash
python test_all_flags.py
```

This tests all SINQ flags to ensure they work correctly with the system.

## Integration Status

✅ **Completed Features:**
- Command line interface with all SINQ flags
- Comprehensive help documentation
- Contextual help examples
- System information integration
- Flag testing integration
- Workflow integration with model selection
- Error handling and fallback mechanisms

The SINQ integration is now fully documented and accessible through the help system, making it easy for users to discover and use quantization features.
