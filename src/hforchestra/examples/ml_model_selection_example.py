"""
Example script demonstrating the ML-based model selection system.

This script shows how to use the machine learning model selection capabilities
to automatically choose the best model for different tasks.
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the path to import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ml_integration import MLIntegrationManager, MLIntegrationConfig, initialize_ml_integration
from core.ensemble_model_selector import EnsembleMethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def demonstrate_ml_model_selection():
    """Demonstrate ML-based model selection with various tasks."""
    
    print("🤖 ML-Based Model Selection Demonstration")
    print("=" * 50)
    
    # Initialize ML integration
    config = MLIntegrationConfig(
        enable_ml_selection=True,
        enable_ensemble_methods=True,
        enable_learning=True,
        default_ensemble_method=EnsembleMethod.WEIGHTED_VOTING,
        performance_tracking=True
    )
    
    ml_manager = initialize_ml_integration(config)
    
    # Example tasks to demonstrate
    example_tasks = [
        {
            'task_name': 'text-generation',
            'prompt': 'Write a short story about a robot learning to paint.',
            'description': 'Creative text generation task'
        },
        {
            'task_name': 'text-classification',
            'prompt': 'This product is amazing! I love it so much. Best purchase ever!',
            'description': 'Sentiment analysis task'
        },
        {
            'task_name': 'summarization',
            'prompt': 'The quick brown fox jumps over the lazy dog. This is a common pangram used in typing practice. It contains every letter of the alphabet at least once.',
            'description': 'Text summarization task'
        },
        {
            'task_name': 'question-answering',
            'prompt': 'What is the capital of France?',
            'description': 'Question answering task'
        },
        {
            'task_name': 'translation',
            'prompt': 'Hello, how are you today?',
            'description': 'Translation task'
        }
    ]
    
    # Test different selection strategies
    strategies = [
        'ml_enhanced',
        'ensemble',
        'voting',
        'consensus',
        'multi_objective'
    ]
    
    for i, task in enumerate(example_tasks, 1):
        print(f"\n📋 Task {i}: {task['description']}")
        print(f"Task Type: {task['task_name']}")
        print(f"Prompt: {task['prompt']}")
        print("-" * 40)
        
        # Test with different strategies
        for strategy in strategies[:2]:  # Test first 2 strategies for brevity
            print(f"\n🎯 Strategy: {strategy}")
            
            try:
                result = await ml_manager.select_best_model(
                    task_name=task['task_name'],
                    prompt=task['prompt'],
                    selection_strategy=strategy,
                    urgency_level=0.7,
                    quality_requirement=0.8
                )
                
                print(f"✅ Selected Model: {result['selected_model']}")
                print(f"📊 Confidence: {result['confidence_score']:.3f}")
                print(f"⏱️  Execution Time: {result['execution_time']:.3f}s")
                print(f"🧠 Reasoning: {result['reasoning']}")
                print(f"📈 Method: {result['method']}")
                
                if result.get('success', False):
                    print("✅ Task completed successfully")
                else:
                    print(f"❌ Task failed: {result.get('error_message', 'Unknown error')}")
                
            except Exception as e:
                print(f"❌ Error with strategy {strategy}: {e}")
        
        print("\n" + "=" * 50)
    
    # Show analytics
    print("\n📊 ML Integration Analytics")
    print("=" * 30)
    
    analytics = ml_manager.get_integration_analytics()
    
    print(f"Total Requests: {analytics['performance_stats']['total_requests']}")
    print(f"ML Selections: {analytics['performance_stats']['ml_selections']}")
    print(f"Ensemble Selections: {analytics['performance_stats']['ensemble_selections']}")
    print(f"Fallback Selections: {analytics['performance_stats']['fallback_selections']}")
    print(f"Successful Selections: {analytics['performance_stats']['successful_selections']}")
    print(f"Average Confidence: {analytics['performance_stats']['average_confidence']:.3f}")
    print(f"Average Execution Time: {analytics['performance_stats']['average_execution_time']:.3f}s")
    
    # Training analytics
    training_analytics = analytics['training_analytics']
    if 'total_training_samples' in training_analytics:
        print(f"\nTraining Data:")
        print(f"Total Samples: {training_analytics['total_training_samples']}")
        print(f"Unique Tasks: {training_analytics['unique_task_types']}")
        print(f"Unique Models: {training_analytics['unique_models']}")
        print(f"Queue Size: {training_analytics['queue_size']}")
    
    # Cleanup
    ml_manager.shutdown()
    print("\n✅ Demonstration completed successfully!")

async def demonstrate_ensemble_methods():
    """Demonstrate different ensemble methods."""
    
    print("\n🎭 Ensemble Methods Demonstration")
    print("=" * 40)
    
    config = MLIntegrationConfig(
        enable_ensemble_methods=True,
        enable_learning=False  # Disable learning for this demo
    )
    
    ml_manager = initialize_ml_integration(config)
    
    # Test ensemble methods
    ensemble_methods = [
        'voting',
        'ensemble',
        'consensus',
        'stacking'
    ]
    
    test_task = {
        'task_name': 'text-classification',
        'prompt': 'This movie was absolutely terrible. Worst film I have ever seen.',
        'description': 'Negative sentiment classification'
    }
    
    print(f"Test Task: {test_task['description']}")
    print(f"Prompt: {test_task['prompt']}")
    print("-" * 40)
    
    for method in ensemble_methods:
        print(f"\n🎯 Ensemble Method: {method}")
        
        try:
            result = await ml_manager.select_best_model(
                task_name=test_task['task_name'],
                prompt=test_task['prompt'],
                selection_strategy=method
            )
            
            print(f"✅ Selected Model: {result['selected_model']}")
            print(f"📊 Confidence: {result['confidence_score']:.3f}")
            print(f"🧠 Reasoning: {result['reasoning']}")
            
            if 'ensemble_details' in result:
                details = result['ensemble_details']
                print(f"🎭 Ensemble Details:")
                print(f"   Method: {details['method']}")
                print(f"   Individual Results: {details['individual_results']}")
                print(f"   Consensus Strength: {details['consensus_strength']:.3f}")
            
        except Exception as e:
            print(f"❌ Error with method {method}: {e}")
    
    ml_manager.shutdown()
    print("\n✅ Ensemble demonstration completed!")

async def demonstrate_learning_capabilities():
    """Demonstrate the learning capabilities of the system."""
    
    print("\n🧠 Learning Capabilities Demonstration")
    print("=" * 45)
    
    config = MLIntegrationConfig(
        enable_learning=True,
        enable_ml_selection=True,
        performance_tracking=True
    )
    
    ml_manager = initialize_ml_integration(config)
    
    # Simulate multiple tasks to build learning data
    learning_tasks = [
        ('text-generation', 'Write a haiku about programming.'),
        ('text-classification', 'This is a great product!'),
        ('summarization', 'The weather today is sunny and warm.'),
        ('question-answering', 'What is machine learning?'),
        ('text-generation', 'Explain quantum computing in simple terms.'),
    ]
    
    print("Training the system with example tasks...")
    
    for i, (task_name, prompt) in enumerate(learning_tasks, 1):
        print(f"\n📚 Learning Task {i}: {task_name}")
        
        try:
            result = await ml_manager.select_best_model(
                task_name=task_name,
                prompt=prompt,
                selection_strategy='ml_enhanced'
            )
            
            print(f"✅ Model: {result['selected_model']}")
            print(f"📊 Confidence: {result['confidence_score']:.3f}")
            
            # Simulate user feedback (in real usage, this would come from actual user ratings)
            if result.get('success', False):
                print("👍 Simulated positive feedback")
            else:
                print("👎 Simulated negative feedback")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Show learning analytics
    print("\n📊 Learning Analytics:")
    analytics = ml_manager.get_integration_analytics()
    training_analytics = analytics['training_analytics']
    
    if 'total_training_samples' in training_analytics:
        print(f"Training Samples Collected: {training_analytics['total_training_samples']}")
        print(f"Queue Size: {training_analytics['queue_size']}")
        print(f"Learning Active: {training_analytics.get('training_in_progress', False)}")
    
    ml_manager.shutdown()
    print("\n✅ Learning demonstration completed!")

async def main():
    """Main demonstration function."""
    try:
        # Run all demonstrations
        await demonstrate_ml_model_selection()
        await demonstrate_ensemble_methods()
        await demonstrate_learning_capabilities()
        
        print("\n🎉 All demonstrations completed successfully!")
        print("\nThe ML-based model selection system is now ready to use!")
        print("\nTo integrate with your existing HFOrchestra system:")
        print("1. Import the MLIntegrationManager from core.ml_integration")
        print("2. Initialize with your desired configuration")
        print("3. Use select_best_model() method for intelligent model selection")
        print("4. The system will learn and improve over time!")
        
    except Exception as e:
        logger.error(f"Error in demonstration: {e}")
        print(f"❌ Demonstration failed: {e}")

if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
