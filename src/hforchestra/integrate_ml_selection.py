"""
Integration script to add ML-based model selection to existing HFOrchestra system.

This script demonstrates how to integrate the ML model selection system
with your existing HFOrchestra infrastructure.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from core.ml_integration import initialize_ml_integration, MLIntegrationConfig
from core.ensemble_model_selector import EnsembleMethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def integrate_with_existing_system():
    """Demonstrate integration with existing HFOrchestra system."""
    
    print("🔗 Integrating ML Model Selection with HFOrchestra")
    print("=" * 55)
    
    # Step 1: Initialize ML Integration
    print("\n1️⃣ Initializing ML Integration System...")
    
    config = MLIntegrationConfig(
        enable_ml_selection=True,
        enable_ensemble_methods=True,
        enable_learning=True,
        default_ensemble_method=EnsembleMethod.WEIGHTED_VOTING,
        fallback_to_enhanced=True,
        performance_tracking=True
    )
    
    ml_manager = initialize_ml_integration(config)
    print("✅ ML Integration System initialized successfully!")
    
    # Step 2: Test with existing task types
    print("\n2️⃣ Testing with existing HFOrchestra task types...")
    
    # Common HFOrchestra task types
    hf_tasks = [
        {
            'task_name': 'text-generation',
            'prompt': 'Generate a creative story about artificial intelligence.',
            'expected_models': ['gpt2', 'gpt2-medium', 'distilgpt2']
        },
        {
            'task_name': 'text-classification',
            'prompt': 'This product is absolutely amazing! I love it!',
            'expected_models': ['distilbert-base-uncased', 'bert-base-uncased']
        },
        {
            'task_name': 'summarization',
            'prompt': 'Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.',
            'expected_models': ['facebook/bart-large-cnn', 't5-base']
        },
        {
            'task_name': 'question-answering',
            'prompt': 'What is the capital of Japan?',
            'expected_models': ['distilbert-base-cased-distilled-squad', 'bert-base-cased']
        },
        {
            'task_name': 'translation',
            'prompt': 'Hello, how are you today?',
            'expected_models': ['Helsinki-NLP/opus-mt-en-es', 't5-base']
        }
    ]
    
    # Test each task type
    for i, task in enumerate(hf_tasks, 1):
        print(f"\n📋 Testing Task {i}: {task['task_name']}")
        print(f"   Prompt: {task['prompt'][:50]}...")
        
        try:
            # Test ML-enhanced selection
            result = await ml_manager.select_best_model(
                task_name=task['task_name'],
                prompt=task['prompt'],
                selection_strategy='ml_enhanced'
            )
            
            print(f"   ✅ Selected Model: {result['selected_model']}")
            print(f"   📊 Confidence: {result['confidence_score']:.3f}")
            print(f"   🧠 Method: {result['method']}")
            print(f"   ⏱️  Execution Time: {result['execution_time']:.3f}s")
            
            # Check if selected model is in expected models
            if result['selected_model'] in task['expected_models']:
                print(f"   🎯 Model selection matches expectations!")
            else:
                print(f"   ⚠️  Model selection differs from expectations")
                print(f"   📝 Expected: {task['expected_models']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Step 3: Test ensemble methods
    print("\n3️⃣ Testing Ensemble Methods...")
    
    ensemble_methods = ['voting', 'consensus', 'ensemble']
    test_task = hf_tasks[0]  # Use first task for ensemble testing
    
    for method in ensemble_methods:
        print(f"\n🎭 Testing {method} ensemble...")
        
        try:
            result = await ml_manager.select_best_model(
                task_name=test_task['task_name'],
                prompt=test_task['prompt'],
                selection_strategy=method
            )
            
            print(f"   ✅ Selected Model: {result['selected_model']}")
            print(f"   📊 Confidence: {result['confidence_score']:.3f}")
            print(f"   🧠 Reasoning: {result['reasoning']}")
            
            if 'ensemble_details' in result:
                details = result['ensemble_details']
                print(f"   🎭 Consensus Strength: {details['consensus_strength']:.3f}")
                print(f"   📊 Individual Results: {details['individual_results']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Step 4: Show integration analytics
    print("\n4️⃣ Integration Analytics...")
    
    analytics = ml_manager.get_integration_analytics()
    
    print(f"\n📊 Performance Statistics:")
    print(f"   Total Requests: {analytics['performance_stats']['total_requests']}")
    print(f"   ML Selections: {analytics['performance_stats']['ml_selections']}")
    print(f"   Ensemble Selections: {analytics['performance_stats']['ensemble_selections']}")
    print(f"   Fallback Selections: {analytics['performance_stats']['fallback_selections']}")
    print(f"   Successful Selections: {analytics['performance_stats']['successful_selections']}")
    print(f"   Average Confidence: {analytics['performance_stats']['average_confidence']:.3f}")
    print(f"   Average Execution Time: {analytics['performance_stats']['average_execution_time']:.3f}s")
    
    # Training data statistics
    training_analytics = analytics['training_analytics']
    if 'total_training_samples' in training_analytics:
        print(f"\n📚 Training Data:")
        print(f"   Total Samples: {training_analytics['total_training_samples']}")
        print(f"   Unique Tasks: {training_analytics['unique_task_types']}")
        print(f"   Unique Models: {training_analytics['unique_models']}")
        print(f"   Queue Size: {training_analytics['queue_size']}")
    
    # Step 5: Integration recommendations
    print("\n5️⃣ Integration Recommendations...")
    
    print("\n💡 To integrate with your existing HFOrchestra system:")
    print("   1. Import the MLIntegrationManager in your main.py")
    print("   2. Initialize it with your preferred configuration")
    print("   3. Replace existing model selection calls with ML-enhanced selection")
    print("   4. Monitor performance and adjust configuration as needed")
    
    print("\n🔧 Example integration code:")
    print("""
    # In your main.py or task handler
    from core.ml_integration import get_ml_integration_manager
    
    # Initialize (do this once at startup)
    ml_manager = get_ml_integration_manager()
    
    # Use in your task processing
    async def process_task_with_ml(task_name, prompt, **kwargs):
        result = await ml_manager.select_best_model(
            task_name=task_name,
            prompt=prompt,
            selection_strategy='ml_enhanced',
            **kwargs
        )
        
        if result['success']:
            # Process with selected model
            return await execute_with_model(
                result['selected_model'], 
                task_name, 
                prompt, 
                **kwargs
            )
        else:
            # Fallback to existing method
            return await process_task_fallback(task_name, prompt, **kwargs)
    """)
    
    # Cleanup
    ml_manager.shutdown()
    
    print("\n✅ Integration demonstration completed successfully!")
    print("\n🚀 Your HFOrchestra system is now ready for ML-enhanced model selection!")

async def main():
    """Main integration function."""
    try:
        await integrate_with_existing_system()
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        print(f"❌ Integration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
