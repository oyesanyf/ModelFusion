# HFOrchestra Test Suite

Comprehensive testing framework for validating all command line options in HFOrchestra.

## 🚀 Quick Start

### Run All Tests
```bash
python run_tests.py
```

### Test Individual Options
```bash
python tests/quick_test.py
```

### Test Specific Categories
```bash
python tests/quick_test.py basic      # Test basic options
python tests/quick_test.py text       # Test text processing
python tests/quick_test.py security   # Test security tasks
python tests/quick_test.py database   # Test database functions
python tests/quick_test.py advanced   # Test advanced features
```

### Test Single Command
```bash
python tests/quick_test.py --stats
python tests/quick_test.py "--prompt 'What is AI?'"
```

## 📋 Test Categories

### Basic Options
- `--help` - Show help information
- `--prompt` - Process text prompts
- `--task` - Alias for --prompt
- `--budget` - Set cost budget
- `--verbose` - Enable detailed logging
- `--language` - Set processing language

### Database Options  
- `--stats` - Show database statistics
- `--tasks` - List available tasks
- `--clearcache` - Clear cached data
- `--update` - Update model database (long running)

### Text Processing Tasks
- `--text-classification` - Classify text content
- `--sentiment` - Sentiment analysis  
- `--question-answering` - Answer questions
- `--summarization` - Text summarization
- `--translation` - Language translation
- `--ner` - Named entity recognition

### Security Tasks
- `--spam-detection` - Detect spam content
- `--pii-detection` - Detect personal information
- `--malware-text-detection` - Detect malicious text
- `--phishing-detection` - Detect phishing attempts

### File Processing
- `--file` - Universal file processing (100+ formats)
- `--pe-header-extraction` - PE binary analysis
- Image files with `--image-classification`
- Audio files with `--automatic-speech-recognition`

### Advanced Features
- `--demo-hyde` - HYDE demonstration
- `--search-query` - Semantic search
- `--analytics-demo` - Advanced analytics demo
- `--model-ranking` - Show model rankings
- `--model-recommendations` - Get model recommendations

## 🧪 Test Files

### `test_command_line_options.py`
Comprehensive pytest unit tests for all command line options.

### `test_runner.py`
Systematic test runner that executes real commands and measures results.

### `quick_test.py`
Interactive tester for rapid validation of individual options.

### `run_tests.py`
Main test orchestrator with multiple testing modes.

## 📊 Expected Results

### ✅ Fully Working (85-90%)
Most command line options are fully functional:
- Basic system operations
- Database functions  
- Text processing tasks
- File analysis
- Security detection
- Advanced analytics

### ⚠️ Conditional (5-10%)
Some options require additional libraries:
- Image processing (requires opencv, PIL)
- Audio processing (requires librosa, soundfile)
- Advanced ML features (requires transformers, torch)

### 🔄 Intelligent Fallbacks (5%)
Some specialized tasks provide simulated responses when models aren't available.

## 🔧 Installation

### Install Test Dependencies
```bash
pip install -r tests/requirements.txt
```

### Install Optional Dependencies
```bash
# For image processing
pip install opencv-python pillow

# For audio processing  
pip install librosa soundfile

# For ML features
pip install transformers torch torchvision

# For PE analysis
pip install pefile magika
```

## 📈 Usage Examples

### Quick Function Verification
```bash
# Test if basic functionality works
python main.py --stats
python main.py --prompt "What is artificial intelligence?"
python main.py --tasks text

# Test file processing
echo "Sample text" > test.txt
python main.py --file test.txt --prompt "Analyze this file"

# Test security features
python main.py --spam-detection --prompt "WIN FREE MONEY NOW!"
```

### Comprehensive Testing
```bash
# Run full test suite
python run_tests.py comprehensive

# Run unit tests only
python run_tests.py unit

# Generate functionality report
python run_tests.py report
```

### Interactive Testing
```bash
# Start interactive mode
python tests/quick_test.py

# Commands in interactive mode:
> list                    # Show all options
> test basic             # Test basic options group
> run --stats            # Test specific command
> quit                   # Exit
```

## 🎯 Key Testing Features

1. **Real Command Execution**: Tests run actual command line calls
2. **Timeout Protection**: Commands are limited to prevent hanging
3. **Error Handling**: Graceful handling of failures and missing dependencies
4. **Detailed Reporting**: JSON output with execution times and results
5. **Categorized Testing**: Organized by functionality groups
6. **Interactive Mode**: Manual testing of individual options

## 📝 Interpreting Results

- **✅ PASS**: Command executed successfully (exit code 0)
- **❌ FAIL**: Command failed or timed out
- **⚠️ WARNING**: Command ran but with warnings/errors in output
- **🔄 TIMEOUT**: Command exceeded time limit

The test suite is designed to validate that HFOrchestra's extensive command line interface works as documented and provides useful functionality for AI task processing.
