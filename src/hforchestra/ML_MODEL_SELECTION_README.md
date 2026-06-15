# ML-Based Model Selection System for HFOrchestra

## Overview

This machine learning-based model selection system enhances HFOrchestra by automatically learning which models perform best for different types of tasks. The system uses historical performance data, task characteristics, and ensemble methods to make intelligent model selection decisions.

## Key Features

### 🤖 Intelligent Model Selection
- **ML-Based Selection**: Uses machine learning models trained on historical performance data
- **Feature Engineering**: Extracts meaningful features from task characteristics (prompt complexity, domain, urgency, etc.)
- **Performance Learning**: Continuously learns from task execution results and user feedback

### 🎭 Ensemble Methods
- **Voting Ensemble**: Simple majority voting across different selection strategies
- **Weighted Voting**: Weighted combination based on historical performance
- **Consensus Ensemble**: Requires strong agreement among selection methods
- **Stacking Ensemble**: Meta-learning approach with secondary models
- **Adaptive Ensemble**: Adjusts weights based on task type

### 📊 Performance Tracking
- **Real-time Learning**: Collects performance data during task execution
- **Model Persistence**: Saves trained models and retrains periodically
- **Analytics Dashboard**: Comprehensive performance analytics and insights

### 🔄 Seamless Integration
- **Backward Compatible**: Works with existing HFOrchestra infrastructure
- **Fallback Support**: Graceful degradation to existing selection methods
- **Configurable**: Highly configurable for different use cases

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ML Integration Manager                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   ML Selector   │  │ Ensemble Selector│  │ Training Mgr │ │
│  │                 │  │                 │  │              │ │
│  │ • Feature Eng.  │  │ • Voting        │  │ • Data Coll. │ │
│  │ • ML Models     │  │ • Weighted      │  │ • Model Train│ │
│  │ • Performance   │  │ • Consensus     │  │ • Persistence│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│              Enhanced Model Selector (Existing)             │
└─────────────────────────────────────────────────────────────┘
```

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements_ml.txt
   ```

2. **Verify Installation**:
   ```bash
   python examples/ml_model_selection_example.py
   ```

## Quick Start

### Basic Usage

```python
from core.ml_integration import initialize_ml_integration, MLIntegrationConfig
from core.ensemble_model_selector import EnsembleMethod

# Initialize the ML system
config = MLIntegrationConfig(
    enable_ml_selection=True,
    enable_ensemble_methods=True,
    enable_learning=True,
    default_ensemble_method=EnsembleMethod.WEIGHTED_VOTING
)

ml_manager = initialize_ml_integration(config)

# Use ML-based model selection
result = await ml_manager.select_best_model(
    task_name='text-generation',
    prompt='Write a story about AI',
    selection_strategy='ml_enhanced'
)

print(f"Selected Model: {result['selected_model']}")
print(f"Confidence: {result['confidence_score']}")
print(f"Reasoning: {result['reasoning']}")
```

### Integration with Existing Code

```python
# In your existing task handler
from core.ml_integration import get_ml_integration_manager

async def handle_task_with_ml(self, task_name: str, prompt: str, **kwargs):
    # Get ML integration manager
    ml_manager = get_ml_integration_manager()
    
    # Use ML selection
    result = await ml_manager.select_best_model(
        task_name=task_name,
        prompt=prompt,
        selection_strategy='ml_enhanced',
        **kwargs
    )
    
    if result['success']:
        # Process with selected model
        return await self.process_with_model(
            result['selected_model'], 
            task_name, 
            prompt, 
            **kwargs
        )
    else:
        # Fallback to existing method
        return await self.handle_task_fallback(task_name, prompt, **kwargs)
```

## Configuration Options

### MLIntegrationConfig

```python
@dataclass
class MLIntegrationConfig:
    enable_ml_selection: bool = True          # Enable ML-based selection
    enable_ensemble_methods: bool = True      # Enable ensemble methods
    enable_learning: bool = True              # Enable learning from feedback
    default_ensemble_method: EnsembleMethod = EnsembleMethod.WEIGHTED_VOTING
    fallback_to_enhanced: bool = True         # Fallback to existing selector
    performance_tracking: bool = True         # Track performance metrics
```

### ModelTrainingConfig

```python
@dataclass
class ModelTrainingConfig:
    min_samples: int = 50                     # Minimum samples for training
    retrain_interval_hours: int = 24          # Retraining frequency
    validation_split: float = 0.2             # Validation data split
    cross_validation_folds: int = 5           # CV folds
    feature_selection_threshold: float = 0.01 # Feature importance threshold
    model_types: List[str] = None             # ML model types to use
```

## Selection Strategies

### 1. ML-Enhanced Selection (`ml_enhanced`)
- Uses trained ML models to predict model performance
- Considers task features, prompt characteristics, and historical data
- Continuously learns and improves

### 2. Ensemble Methods
- **`voting`**: Simple majority voting
- **`ensemble`**: Weighted voting (default)
- **`consensus`**: Requires strong agreement
- **`stacking`**: Meta-learning approach
- **`adaptive`**: Task-specific weight adjustment

### 3. Enhanced Fallback
- **`multi_objective`**: Multi-objective optimization
- **`hyperparameter_tuning`**: Hyperparameter optimization
- **`cross_validation`**: Cross-validation based selection
- **`bayesian_optimization`**: Bayesian optimization
- **`meta_learning`**: Meta-learning approach

## Feature Engineering

The system extracts the following features from tasks:

### Task Features
- **Task Type**: Type of task (text-generation, classification, etc.)
- **Prompt Length**: Length of the input prompt
- **Prompt Complexity**: Complexity score based on keywords and structure
- **Language**: Detected language of the prompt
- **Domain**: Detected domain (technical, creative, analytical, etc.)

### Resource Features
- **Urgency Level**: How urgent the task is (0-1)
- **Quality Requirement**: Required quality level (0-1)
- **Resource Constraint**: Resource limitations (0-1)

### Content Features
- **Has Code**: Whether prompt contains code
- **Has Math**: Whether prompt contains mathematical content
- **Has Tables**: Whether prompt contains tabular data
- **Has Images**: Whether task involves images
- **File Type**: Type of input file (if any)
- **File Size**: Size of input file (if any)

## Performance Metrics

The system tracks and learns from:

- **Accuracy Score**: How accurate the model's output was
- **Quality Score**: User-rated quality of the output
- **Execution Time**: Time taken to complete the task
- **Resource Usage**: Memory/CPU usage during execution
- **Cost**: Estimated cost of using the model
- **Success Rate**: Whether the task completed successfully

## Analytics and Monitoring

### Get Performance Analytics

```python
analytics = ml_manager.get_integration_analytics()

print(f"Total Requests: {analytics['performance_stats']['total_requests']}")
print(f"ML Selections: {analytics['performance_stats']['ml_selections']}")
print(f"Average Confidence: {analytics['performance_stats']['average_confidence']}")
print(f"Training Samples: {analytics['training_analytics']['total_training_samples']}")
```

### Training Analytics

```python
training_analytics = ml_manager.training_manager.get_training_analytics()

print(f"Total Training Samples: {training_analytics['total_training_samples']}")
print(f"Unique Task Types: {training_analytics['unique_task_types']}")
print(f"Unique Models: {training_analytics['unique_models']}")
print(f"Recent Training Sessions: {training_analytics['recent_training_sessions']}")
```

## Advanced Usage

### Custom Ensemble Methods

```python
# Create custom ensemble configuration
custom_config = MLIntegrationConfig(
    enable_ensemble_methods=True,
    default_ensemble_method=EnsembleMethod.CONSENSUS
)

ml_manager = initialize_ml_integration(custom_config)

# Use consensus-based selection
result = await ml_manager.select_best_model(
    task_name='text-classification',
    prompt='This is a test prompt',
    selection_strategy='consensus'
)
```

### Force Model Retraining

```python
# Force immediate retraining
ml_manager.force_retrain_models()
```

### Cleanup Old Data

```python
# Clean up data older than 30 days
ml_manager.cleanup_old_data(days_to_keep=30)
```

### Batch Processing

```python
# Process multiple tasks in batch
tasks = [
    ('text-generation', 'Write a story'),
    ('text-classification', 'Classify this text'),
    ('summarization', 'Summarize this document')
]

results = await ml_manager.batch_process_tasks(
    tasks, 
    selection_strategy='ml_enhanced'
)
```

## Database Schema

### Training Data Table
```sql
CREATE TABLE training_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    selected_model TEXT NOT NULL,
    actual_performance TEXT NOT NULL,
    task_features TEXT NOT NULL,
    user_feedback TEXT,
    timestamp REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Model Performance Tracking
```sql
CREATE TABLE model_performance_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    accuracy REAL,
    precision REAL,
    recall REAL,
    f1_score REAL,
    training_time REAL,
    validation_score REAL,
    timestamp REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Common Issues

1. **Insufficient Training Data**
   - The system needs at least 50 samples to train effectively
   - Use the system for a while to collect training data
   - Check `training_analytics['total_training_samples']`

2. **Low Confidence Scores**
   - This is normal for new tasks or models
   - The system will improve as it learns
   - Consider using ensemble methods for better reliability

3. **Performance Issues**
   - ML selection adds some overhead
   - Consider disabling learning in production if not needed
   - Use fallback methods for critical tasks

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging to see detailed information
```

### Performance Monitoring

```python
# Monitor performance statistics
analytics = ml_manager.get_integration_analytics()
print(f"Average execution time: {analytics['performance_stats']['average_execution_time']:.3f}s")
print(f"Success rate: {analytics['performance_stats']['successful_selections'] / analytics['performance_stats']['total_requests']:.2%}")
```

## Best Practices

### 1. Gradual Rollout
- Start with a small percentage of tasks using ML selection
- Monitor performance and gradually increase usage
- Keep fallback methods enabled

### 2. Data Quality
- Ensure accurate performance feedback
- Regularly review and clean training data
- Monitor for data drift

### 3. Model Maintenance
- Regularly retrain models with new data
- Monitor model performance over time
- Update feature engineering as needed

### 4. Resource Management
- Monitor resource usage of ML components
- Clean up old data periodically
- Use appropriate model complexity for your needs

## Future Enhancements

### Planned Features
- **Deep Learning Models**: Integration with neural networks
- **Online Learning**: Real-time model updates
- **Multi-Modal Selection**: Support for image, audio, and video tasks
- **Federated Learning**: Distributed learning across multiple instances
- **A/B Testing**: Built-in experimentation framework

### Extensibility
- **Custom Feature Extractors**: Add domain-specific features
- **Custom Ensemble Methods**: Implement new ensemble strategies
- **Custom ML Models**: Add new machine learning algorithms
- **Custom Metrics**: Define task-specific performance metrics

## Contributing

1. **Feature Requests**: Submit issues for new features
2. **Bug Reports**: Report bugs with detailed information
3. **Code Contributions**: Submit pull requests for improvements
4. **Documentation**: Help improve documentation and examples

## License

This ML model selection system is part of HFOrchestra and follows the same license terms.

## Support

For support and questions:
- Check the troubleshooting section
- Review the example scripts
- Submit issues on the project repository
- Contact the development team

---

**Happy Model Selecting! 🚀**
