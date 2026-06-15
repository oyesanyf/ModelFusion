#!/usr/bin/env python3
"""
Test script for chain-of-thought functionality
"""

import asyncio
import os
import sys

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_chain_of_thought():
    """Test chain-of-thought functionality."""
    
    print("🧠 Testing Chain-of-Thought Functionality")
    print("=" * 50)
    
    try:
        # Import the orchestrator
        from core.orchestrator import HuggingFaceOrchestrator
        
        # Create orchestrator
        orchestrator = HuggingFaceOrchestrator(
            budget=10.0,
            enable_ml=False,
            verbose=True
        )
        
        # Test parameters
        test_prompt = "List three colors"
        test_kwargs = {
            'chain_of_thought': True,
            'task_name': 'text-generation'
        }
        
        print(f"📝 Test prompt: {test_prompt}")
        print(f"🔗 Chain of thought: {test_kwargs.get('chain_of_thought')}")
        print(f"📋 Task name: {test_kwargs.get('task_name')}")
        print()
        
        # Process the task
        print("🚀 Processing task...")
        result = await orchestrator.process_task(test_prompt, **test_kwargs)
        
        print("\n📊 Results:")
        print(f"✅ Success: {result.success}")
        print(f"📝 Content: {result.content[:200]}...")
        print(f"🤖 Models used: {result.models_used}")
        print(f"⏱️ Processing time: {result.total_latency_ms:.2f}ms")
        
        if result.error_message:
            print(f"❌ Error: {result.error_message}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enhanced_orchestrator():
    """Test enhanced orchestrator with chain-of-thought."""
    
    print("\n🧠 Testing Enhanced Orchestrator with Chain-of-Thought")
    print("=" * 60)
    
    try:
        # Import the enhanced orchestrator
        from core.enhanced_orchestrator import EnhancedOrchestrator
        
        # Create enhanced orchestrator
        orchestrator = EnhancedOrchestrator(
            budget=10.0,
            enable_ml=False,
            verbose=True
        )
        
        # Test parameters
        test_prompt = "List three colors"
        test_kwargs = {
            'chain_of_thought': True,
            'task_name': 'text-generation',
            'selection_strategy': 'ensemble_methods'
        }
        
        print(f"📝 Test prompt: {test_prompt}")
        print(f"🔗 Chain of thought: {test_kwargs.get('chain_of_thought')}")
        print(f"📋 Task name: {test_kwargs.get('task_name')}")
        print(f"🎯 Selection strategy: {test_kwargs.get('selection_strategy')}")
        print()
        
        # Process the task
        print("🚀 Processing task with enhanced orchestrator...")
        result = await orchestrator.process_task(test_prompt, **test_kwargs)
        
        print("\n📊 Results:")
        print(f"✅ Success: {result.success}")
        print(f"📝 Content: {result.content[:200]}...")
        print(f"🤖 Models used: {result.models_used}")
        print(f"⏱️ Processing time: {result.processing_time_ms:.2f}ms")
        
        if result.error_message:
            print(f"❌ Error: {result.error_message}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Error during enhanced testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    
    print("🧪 Chain-of-Thought Test Suite")
    print("=" * 40)
    
    # Test 1: Basic orchestrator
    print("\n🔬 Test 1: Basic Orchestrator")
    success1 = await test_chain_of_thought()
    
    # Test 2: Enhanced orchestrator
    print("\n🔬 Test 2: Enhanced Orchestrator")
    success2 = await test_enhanced_orchestrator()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"✅ Basic Orchestrator: {'PASS' if success1 else 'FAIL'}")
    print(f"✅ Enhanced Orchestrator: {'PASS' if success2 else 'FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Chain-of-thought is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())
