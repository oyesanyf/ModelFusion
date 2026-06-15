# HFOrchestra - Modular Architecture

HFOrchestra has been restructured into a modular architecture for better organization, maintainability, and extensibility. This document describes the new structure and how to use it.

## 📁 Directory Structure

```
HFOrchestra/
├── __init__.py                 # Main package initialization
├── main.py                     # Entry point for the application
├── core/                       # Core system components
│   ├── __init__.py
│   ├── orchestrator.py         # Main orchestrator class
│   └── providers.py            # LLM provider implementations
├── security/                   # Security and threat detection
│   ├── __init__.py
│   └── atlas_detector.py       # ATLAS threat detection
├── monitoring/                 # System monitoring and evaluation
│   ├── __init__.py
│   └── tree_monitor.py         # Decision monitoring and evaluation
├── models/                     # Model management
│   ├── __init__.py
│   ├── discovery.py            # Model discovery and database
│   ├── database.py             # Database management
│   └── selector.py             # Model selection algorithms
├── tasks/                      # Task processing
│   ├── __init__.py
│   ├── processor.py            # Universal task processor
│   ├── delegation.py           # Task delegation management
│   └── recursive.py            # Recursive task handling
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── folder_manager.py       # File and directory management
│   └── performance.py          # Performance monitoring and rate limiting
├── analysis/                   # Analysis modules
│   ├── __init__.py
│   ├── pe_extractor.py         # PE header extraction
│   └── malware_detector.py     # Malware detection
├── interface/                  # User interfaces
│   ├── __init__.py
│   └── cli.py                  # Command-line interface
└── config/                     # Configuration (existing)
    ├── __init__.py
    └── ...                     # Existing config files
```

## 🏗️ Module Overview

### Core Module (`core/`)
Contains the main orchestrator and provider classes that form the foundation of the system.

- **`orchestrator.py`**: Main HuggingFaceOrchestrator class
- **`providers.py`**: LLM provider implementations (OpenAI, Anthropic, Gemini, etc.)

### Security Module (`security/`)
Provides security-related components including ATLAS threat detection.

- **`atlas_detector.py`**: ATLASThreatDetector for identifying adversarial attacks

### Monitoring Module (`monitoring/`)
Contains monitoring and evaluation components for tracking system performance.

- **`tree_monitor.py`**: EnhancedTreeMonitor, DecisionMetrics, AdaptiveThresholdManager

### Models Module (`models/`)
Handles model discovery, selection, and database management.

- **`discovery.py`**: EnhancedHuggingFaceDiscovery, SmartModelSelector, ModelMetrics
- **`database.py`**: HuggingFaceModelDatabase
- **`selector.py`**: HybridModelSelector

### Tasks Module (`tasks/`)
Manages task processing, delegation, and recursive task handling.

- **`processor.py`**: UniversalTaskProcessor
- **`delegation.py`**: DelegationManager, DelegationTask
- **`recursive.py`**: RecursiveTaskManager, RecursiveTask

### Utils Module (`utils/`)
Provides utility components for common operations.

- **`folder_manager.py`**: FolderManager for file operations
- **`performance.py`**: PerformanceMonitor, AdaptiveRateLimiter

### Analysis Module (`analysis/`)
Contains PE header analysis and malware detection capabilities.

- **`pe_extractor.py`**: CompletePEHeaderExtractor
- **`malware_detector.py`**: PEAnalyzer

### Interface Module (`interface/`)
User interface components.

- **`cli.py`**: CLIInterface

## 🚀 Usage

### Basic Usage

```python
from hforchestra import (
    HuggingFaceOrchestrator,
    ATLASThreatDetector,
    PEAnalyzer,
    FolderManager
)

# Initialize components
folder_manager = FolderManager()
detector = ATLASThreatDetector()
analyzer = PEAnalyzer()

# Use the components
threats = detector.scan_thought("some suspicious text")
result = analyzer.analyze_file("suspicious.exe")
```

### Command Line Interface

```bash
# Analyze a file for malware
python main.py --analyze-file malware.exe

# Scan text for ATLAS threats
python main.py --security-scan "suspicious prompt"

# Analyze all PE files in a directory
python main.py --pe-analysis /path/to/files/

# Show performance statistics
python main.py --performance
```

## 🔧 Module Development

### Adding a New Module

1. Create a new directory in the appropriate location
2. Add an `__init__.py` file with proper imports
3. Update the main `__init__.py` to include the new module
4. Document the module in this README

### Example: Adding a New Analysis Module

```python
# analysis/new_analyzer.py
class NewAnalyzer:
    def __init__(self):
        pass
    
    def analyze(self, data):
        # Implementation
        pass

# analysis/__init__.py
from .new_analyzer import NewAnalyzer

__all__ = ['NewAnalyzer']

# __init__.py (main)
from .analysis.new_analyzer import NewAnalyzer
```

## 📊 Benefits of Modular Structure

1. **Maintainability**: Each module has a single responsibility
2. **Testability**: Modules can be tested independently
3. **Extensibility**: New features can be added as new modules
4. **Reusability**: Modules can be used in different contexts
5. **Clarity**: Clear separation of concerns
6. **Documentation**: Each module can be documented separately

## 🔄 Migration from Monolithic Structure

The original `HuggingFace_orhcestrator.py` file has been broken down into logical modules. The functionality remains the same, but it's now organized in a more maintainable way.

### Key Changes

- Classes are now organized by functionality
- Each module has its own `__init__.py` file
- Imports are cleaner and more specific
- Dependencies between modules are explicit

## 🛠️ Development Guidelines

1. **Keep modules focused**: Each module should have a single, well-defined purpose
2. **Use proper imports**: Import only what you need from other modules
3. **Document your code**: Each module should have clear docstrings
4. **Follow naming conventions**: Use consistent naming across modules
5. **Test modules independently**: Each module should be testable on its own

## 📝 Future Enhancements

- Add more specialized analysis modules
- Implement plugin system for extensibility
- Add web interface module
- Create configuration management module
- Add logging and debugging modules

## 🤝 Contributing

When contributing to HFOrchestra:

1. Follow the modular structure
2. Add appropriate `__init__.py` files
3. Update this README if adding new modules
4. Ensure your code follows the established patterns
5. Add tests for new functionality

---

This modular structure makes HFOrchestra more maintainable, extensible, and easier to understand. Each module can be developed, tested, and deployed independently while still working together as a cohesive system. 