#!/usr/bin/env python3
"""
Demonstrate dynamic model selection from database.
"""

from config.dynamic_task_generator import DynamicTaskGenerator

def show_dynamic_selection():
    """Show how models are always selected dynamically."""
    print("🔄 Dynamic Model Selection Demo")
    print("=" * 50)
    
    generator = DynamicTaskGenerator()
    
    # Show top models for different tasks
    tasks = ['text-classification', 'question-answering', 'summarization', 'visual-question-answering']
    
    for task in tasks:
        print(f"\n📊 {task.upper()}:")
        models = generator.get_best_models_for_task(task, 3)
        
        if models:
            for i, model in enumerate(models):
                print(f"  {i+1}. {model['model_id']}")
                print(f"     Downloads: {model['downloads']:,}")
                print(f"     Likes: {model['likes']}")
                print(f"     Score: {model['score']:.3f}")
        else:
            print(f"  ❌ No models found for {task}")
    
    print(f"\n🎯 Key Points:")
    print(f"  • Models are ALWAYS selected from database")
    print(f"  • Rankings update automatically")
    print(f"  • No hardcoded model selections")
    print(f"  • Best models chosen by popularity + recency")

if __name__ == "__main__":
    show_dynamic_selection() 