# PE Analysis with AI-Powered Malware Detection

A comprehensive PE (Portable Executable) file analysis system that combines traditional static analysis with AI-powered malware detection using the best HuggingFace models.

## 🚀 Features

### Core Analysis Capabilities
- **Comprehensive PE Header Analysis**: Extract and analyze all PE headers, sections, and data directories
- **Static Malware Detection**: Identify suspicious patterns, APIs, and anomalies
- **Entropy Analysis**: Detect packed/encrypted content using Shannon entropy
- **Import Analysis**: Analyze imported functions for malicious behavior patterns
- **OTX Integration**: Check file hashes against AlienVault OTX threat intelligence
- **AI-Powered Detection**: Use state-of-the-art HuggingFace models for malware classification

### AI Model Integration
- **Automatic Model Discovery**: Find the best malware detection models from your HuggingFace database
- **Quality Ranking**: Rank models by downloads, likes, scores, and recency
- **Multi-Model Analysis**: Test files against multiple AI models for consensus
- **Confidence Scoring**: Provide confidence levels for AI predictions

### Reporting & Output
- **Comprehensive JSON Reports**: Detailed analysis results in structured format
- **Human-Readable Reports**: Generate executive summaries and security recommendations
- **Multiple Output Formats**: JSON, text reports, and console summaries
- **Timestamped Results**: All reports include analysis timestamps

## 📋 Requirements

### Python Dependencies
```bash
pip install pefile requests asyncio aiohttp sqlite3
```

### Optional Dependencies
- **HuggingFace Token**: For AI model access (set `HF_TOKEN` environment variable)
- **OTX API Key**: For threat intelligence (set `OTX_API_KEY` environment variable)

### System Requirements
- Python 3.7+
- Windows (for PE file analysis)
- Internet connection (for OTX and HuggingFace API calls)

## 🛠️ Installation

1. **Clone or download the scripts**:
   ```bash
   # All scripts should be in your project directory
   ```

2. **Set up environment variables** (optional):
   ```bash
   export HF_TOKEN="your_huggingface_token"
   export OTX_API_KEY="your_otx_api_key"
   ```

3. **Test the installation**:
   ```bash
   python test_pe_analysis.py
   ```

## 📖 Usage

### 1. Find Best Malware Detection Models

Discover and rank the best malware detection models in your HuggingFace database:

```bash
python find_best_malware_models.py
```

**Output**: Lists top malware detection models with quality scores and recommendations.

### 2. Basic PE Analysis

Analyze a PE file with static analysis only:

```bash
python enhanced_pe_analyzer.py path/to/file.exe
```

**Features**:
- PE header extraction
- Section analysis
- Import analysis
- Entropy calculation
- OTX hash checking
- Suspicious pattern detection

### 3. Comprehensive Analysis with AI

Full analysis combining static analysis with AI-powered detection:

```bash
python pe_analysis_with_ai.py path/to/file.exe --save-report
```

**Features**:
- All static analysis features
- AI model discovery and ranking
- Multi-model malware detection
- Comprehensive reporting
- Human-readable security reports

### 4. Command Line Options

```bash
python pe_analysis_with_ai.py <pe_file> [options]

Options:
  --output-dir DIR     Output directory for reports (default: reports)
  --hf-token TOKEN     HuggingFace API token
  --save-report        Generate human-readable security report
  --help              Show help message
```

## 📊 Analysis Results

### Verdict Categories
- **CLEAN**: No malicious indicators detected
- **SUSPICIOUS**: Some concerning patterns found
- **MALICIOUS**: Strong evidence of malicious behavior

### Analysis Components

#### Static Analysis
- **Strong Indicators**: High-confidence malicious patterns
- **Weak Indicators**: Suspicious but not definitive patterns
- **Section Analysis**: Entropy, permissions, and anomalies
- **Import Analysis**: Suspicious API usage patterns
- **Header Anomalies**: PE header inconsistencies

#### AI Analysis
- **Model Consensus**: Multiple AI model predictions
- **Confidence Scores**: Reliability of AI predictions
- **Model Quality**: Ranking of used models

#### Threat Intelligence
- **OTX Results**: Known malicious hash matches
- **Threat Campaigns**: Related threat intelligence
- **Detection Counts**: Number of security vendors flagging the file

## 🔍 Example Output

### Console Summary
```
🔍 COMPREHENSIVE PE ANALYSIS SUMMARY
================================================================================
📁 File: suspicious_file.exe
📏 Size: 1,234,567 bytes
🔐 Static Verdict: SUSPICIOUS
🎯 Final Verdict: MALICIOUS
🔗 SHA256: a1b2c3d4e5f6...

🚨 Strong Indicators (3):
  • High entropy in section: .data (7.8)
  • CreateRemoteThread (process_injection)
  • VirtualAllocEx (process_injection)

⚠️  Weak Indicators (5):
  • Non-standard section name: .packed
  • ASLR not enabled
  • DEP not enabled
  • ...

🌐 OTX Intelligence:
  • Malicious: True
  • Positives: 45
  • Pulses: Ransomware.CryptoLocker, Banking.Trojan

🤖 AI Model Analysis:
  • microsoft/big-vul: 0.85 confidence
  • sibumi/DISTILBERT_static_malware-detection: 0.92 confidence
  • llmrails/ember-v1: 0.78 confidence

🏆 Best Models Used:
  1. sibumi/DISTILBERT_static_malware-detection (Score: 80.0)
  2. microsoft/big-vul (Score: 85.0)
  3. llmrails/ember-v1 (Score: 82.0)
```

### Security Report
```
🔒 PE FILE SECURITY ANALYSIS REPORT
================================================================================

📋 EXECUTIVE SUMMARY
----------------------------------------
File: suspicious_file.exe
Size: 1,234,567 bytes
Final Verdict: MALICIOUS
Analysis Date: 2025-08-03T17:30:00

🚨 THREAT ASSESSMENT
----------------------------------------
❌ HIGH RISK - File appears to be malicious
   • Multiple strong indicators detected
   • Recommend immediate quarantine

🔍 DETAILED FINDINGS
----------------------------------------
Strong Indicators (3):
  • High entropy in section: .data (7.8)
  • CreateRemoteThread (process_injection)
  • VirtualAllocEx (process_injection)

🌐 THREAT INTELLIGENCE (OTX)
----------------------------------------
Known Malicious: True
Positive Detections: 45
Related Threat Campaigns:
  • Ransomware.CryptoLocker
  • Banking.Trojan

💡 SECURITY RECOMMENDATIONS
----------------------------------------
• IMMEDIATE ACTION REQUIRED:
  - Quarantine the file immediately
  - Scan all systems for similar files
  - Review system logs for suspicious activity
  - Consider full system scan
```

## 🏆 Best Malware Detection Models

The system automatically discovers and ranks the best malware detection models:

### Top Recommended Models
1. **microsoft/big-vul** - Vulnerability detection in source code
2. **sibumi/DISTILBERT_static_malware-detection** - Static malware detection
3. **llmrails/ember-v1** - EMBER malware classification
4. **ZySec-AI/SecurityLLM** - Security-focused language model
5. **ehsanaghaei/SecureBERT** - Security text classification

### Model Selection Criteria
- **Downloads**: Popularity and usage
- **Likes**: Community approval
- **Scores**: Model performance metrics
- **Recency**: Recent updates and maintenance
- **Size**: Model efficiency and resource usage

## 🔧 Configuration

### Environment Variables
```bash
# HuggingFace API access
export HF_TOKEN="your_token_here"

# OTX threat intelligence
export OTX_API_KEY="your_key_here"

# Timeout settings
export GLOBAL_TIMEOUT_SECONDS=300
export MODEL_LOAD_TIMEOUT_SECONDS=180
```

### Database Configuration
The system uses your existing HuggingFace model database (`db/hf_models.db`) to find malware detection models.

## 🧪 Testing

Run the test suite to verify installation:

```bash
python test_pe_analysis.py
```

This will test:
- Database connectivity
- Model discovery
- PE analysis functionality
- Comprehensive analysis pipeline

## 📁 Output Files

### Generated Files
- `{filename}_comprehensive_analysis_{timestamp}.json` - Full analysis results
- `{filename}_security_report_{timestamp}.txt` - Human-readable report
- `best_malware_models_{timestamp}.json` - Model discovery results

### Directory Structure
```
reports/
├── file1_comprehensive_analysis_20250803_173000.json
├── file1_security_report_20250803_173000.txt
├── file2_comprehensive_analysis_20250803_174500.json
└── file2_security_report_20250803_174500.txt
```

## 🔒 Security Considerations

### Safe Analysis
- **Static Analysis Only**: No file execution or dynamic analysis
- **Read-Only Access**: Files are only read, never modified
- **Isolated Processing**: Analysis runs in isolated environment

### Privacy & Data
- **Local Processing**: Analysis runs locally on your system
- **Optional APIs**: OTX and HuggingFace APIs are optional
- **No Data Upload**: Files are not uploaded to external services

### Best Practices
- **Sandbox Testing**: Test suspicious files in isolated environments
- **Multiple Tools**: Use alongside other security tools
- **Regular Updates**: Keep models and threat intelligence updated

## 🐛 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check if database exists
ls -la db/hf_models.db

# Recreate database if needed
python populate_all_hf_models.py
```

**HuggingFace API Errors**
```bash
# Check token
echo $HF_TOKEN

# Set token if missing
export HF_TOKEN="your_token_here"
```

**PE Analysis Errors**
```bash
# Check file permissions
ls -la suspicious_file.exe

# Verify file is valid PE
file suspicious_file.exe
```

### Error Messages

- **"File not found"**: Check file path and permissions
- **"Invalid PE file"**: File may be corrupted or not a valid PE
- **"Database error"**: Check database file and permissions
- **"API error"**: Check network connection and API keys

## 🤝 Contributing

### Adding New Models
1. Update the model discovery queries in `find_best_malware_models.py`
2. Add new model categories and scoring criteria
3. Test with sample files

### Improving Analysis
1. Add new suspicious API patterns
2. Enhance entropy analysis algorithms
3. Improve verdict determination logic

### Bug Reports
Please report issues with:
- File path and error message
- Python version and dependencies
- Sample file (if safe to share)

## 📄 License

This project is for educational and security research purposes. Use responsibly and in accordance with applicable laws and regulations.

## 🙏 Acknowledgments

- **HuggingFace**: For providing access to malware detection models
- **AlienVault OTX**: For threat intelligence data
- **pefile library**: For PE file parsing capabilities
- **Security research community**: For malware analysis techniques

---

**⚠️ Disclaimer**: This tool is for security analysis and research purposes. Always use in safe, controlled environments and follow responsible disclosure practices. 