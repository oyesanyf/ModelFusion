# ML-Based Model Selection Flags for HFOrchestra

## Overview

Your HFOrchestra system now includes comprehensive ML-based model selection capabilities with new command-line flags. The system learns from historical performance data to automatically select the best model for each task.

## New ML Flags Added

### Core ML Selection Flags

#### `--enable-ml-selection`
- **Description**: Enable ML-based model selection system that learns from historical performance
- **Usage**: `python main.py --enable-ml-selection --prompt "Your task"`
- **Default**: Disabled
- **Note**: This flag must be used to activate the ML selection system

#### `--ml-learning`
- **Description**: Enable learning from task execution results to improve model selection over time
- **Usage**: `python main.py --enable-ml-selection --ml-learning --prompt "Your task"`
- **Default**: Disabled
- **Note**: Allows the system to learn and improve from your actual usage patterns

### ML Selection Strategy Flags

#### `--selection-strategy` (Enhanced)
- **New Options Added**:
  - `ml_enhanced` - ML-enhanced selection (recommended)
  - `ml_ensemble` - Ensemble-based selection
  - `ml_voting` - Voting ensemble method
  - `ml_consensus` - Consensus-based selection
  - `ml_stacking` - Stacking ensemble method
  - `ml_adaptive` - Adaptive ensemble method

- **Usage Examples**:
  ```bash
  python main.py --enable-ml-selection --selection-strategy ml_enhanced --prompt "Your task"
  python main.py --enable-ml-selection --selection-strategy ml_consensus --prompt "Your task"
  ```

### ML Configuration Flags

#### `--ml-ensemble-method`
- **Description**: Choose the ensemble method for ML-based model selection
- **Options**: `voting`, `weighted_voting`, `consensus`, `stacking`, `adaptive`
- **Default**: `weighted_voting`
- **Usage**: `python main.py --enable-ml-selection --ml-ensemble-method consensus`

#### `--ml-confidence-threshold`
- **Description**: Minimum confidence threshold for ML model selection
- **Range**: 0.0 - 1.0
- **Default**: 0.6
- **Usage**: `python main.py --enable-ml-selection --ml-confidence-threshold 0.8`

#### `--ml-fallback`
- **Description**: Enable fallback to enhanced selector when ML selection fails
- **Default**: True
- **Usage**: `python main.py --enable-ml-selection --ml-fallback`

### ML Management Flags

#### `--ml-analytics`
- **Description**: Show ML model selection analytics and performance statistics
- **Usage**: `python main.py --ml-analytics`
- **Output**: Comprehensive analytics including:
  - Total requests and selection counts
  - Average confidence and execution time
  - Training data statistics
  - Configuration details

#### `--ml-retrain`
- **Description**: Force retraining of ML models with current data
- **Usage**: `python main.py --ml-retrain`
- **Note**: Useful for updating models with new training data

#### `--ml-cleanup DAYS`
- **Description**: Clean up ML training data older than specified days
- **Usage**: `python main.py --ml-cleanup 30`
- **Note**: Helps manage database size by removing old training data

## Usage Examples

### Basic ML-Enhanced Selection
```bash
python main.py --enable-ml-selection --selection-strategy ml_enhanced --prompt "Write a story about AI"
```

### Ensemble Voting Method
```bash
python main.py --enable-ml-selection --ml-ensemble-method voting --selection-strategy ml_voting --prompt "Classify this sentiment"
```

### High Confidence Selection
```bash
python main.py --enable-ml-selection --ml-confidence-threshold 0.8 --selection-strategy ml_consensus --prompt "Translate this text"
```

### Learning-Enabled Selection
```bash
python main.py --enable-ml-selection --ml-learning --selection-strategy ml_adaptive --prompt "Summarize this document"
```

### View ML Analytics
```bash
python main.py --ml-analytics
```

### Force Model Retraining
```bash
python main.py --ml-retrain
```

### Clean Up Old Data
```bash
python main.py --ml-cleanup 30
```

## Integration with Existing Flags

The ML flags work seamlessly with your existing HFOrchestra flags:

```bash
# ML selection with file processing
python main.py --enable-ml-selection --selection-strategy ml_enhanced --file data.csv --prompt "Analyze this data"

# ML selection with chain-of-thought
python main.py --enable-ml-selection --ml-learning --chain-of-thought --prompt "Solve this complex problem"

# ML selection with specific language
python main.py --enable-ml-selection --selection-strategy ml_consensus --language es --prompt "Translate to Spanish"
```

## How It Works

1. **Initialization**: When `--enable-ml-selection` is used, the ML system initializes
2. **Model Selection**: The system uses ML models to predict the best model for your task
3. **Learning**: If `--ml-learning` is enabled, the system learns from task results
4. **Fallback**: If ML selection fails, it falls back to your existing enhanced selector
5. **Analytics**: Use `--ml-analytics` to monitor performance and learning progress

## Performance Benefits

- **Automatic Optimization**: Learns which models work best for different tasks
- **Improved Accuracy**: Better model selection leads to better results
- **Reduced Manual Tuning**: Less need for manual model selection
- **Continuous Learning**: Gets better over time as it learns from more data
- **Robust Selection**: Ensemble methods provide more reliable selections

## Dependencies

To use the ML selection system, install the required dependencies:

```bash
pip install -r requirements_ml.txt
```

Required packages:
- numpy
- pandas
- scikit-learn
- scipy
- joblib

## Troubleshooting

### ML System Not Available
If you see "ML selection system not available", install the dependencies:
```bash
pip install -r requirements_ml.txt
```

### Low Confidence Scores
This is normal for new tasks. The system improves as it learns from more data.

### Performance Issues
- Consider disabling learning in production: `--enable-ml-selection` (without `--ml-learning`)
- Use fallback methods for critical tasks
- Monitor with `--ml-analytics`

## Best Practices

1. **Start Small**: Begin with a few tasks using ML selection
2. **Enable Learning**: Use `--ml-learning` to let the system improve
3. **Monitor Performance**: Regularly check `--ml-analytics`
4. **Clean Up Data**: Periodically use `--ml-cleanup` to manage database size
5. **Fallback Enabled**: Keep `--ml-fallback` enabled for reliability

## Advanced Configuration

For advanced users, you can customize the ML system by modifying the configuration in the code:

```python
# In core/ml_integration.py
ml_config = MLIntegrationConfig(
    enable_ml_selection=True,
    enable_ensemble_methods=True,
    enable_learning=True,
    default_ensemble_method=EnsembleMethod.WEIGHTED_VOTING,
    fallback_to_enhanced=True,
    performance_tracking=True
)
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the ML_MODEL_SELECTION_README.md for detailed documentation
3. Run the example scripts in the examples/ directory
4. Use `--ml-analytics` to monitor system performance

---

**Happy ML-Enhanced Model Selecting! 🚀🤖**
