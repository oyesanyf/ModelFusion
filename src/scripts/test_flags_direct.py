#!/usr/bin/env python3
"""
Direct Flag Testing Script for HFOrchestra

This script tests flags by importing and calling functions directly instead of using subprocess.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class DirectFlagTester:
    def __init__(self):
        self.results = {}
        self.failed_flags = []
        self.passed_flags = []
        
    async def test_flag(self, flag_name, test_function, expected_behavior="should not crash"):
        """Test a single flag using a test function."""
        print(f"🧪 Testing flag: {flag_name}")
        
        try:
            # Run the test function
            result = await test_function()
            
            if result:
                print(f"   ✅ PASS: {flag_name} - {expected_behavior}")
                self.passed_flags.append(flag_name)
                return True
            else:
                print(f"   ❌ FAIL: {flag_name} - Test function returned False")
                self.failed_flags.append(flag_name)
                return False
                
        except Exception as e:
            print(f"   💥 ERROR: {flag_name} - {str(e)}")
            self.failed_flags.append(flag_name)
            return False

    async def test_help_flag(self):
        """Test --help flag."""
        try:
            from main import main
            # This should work without crashing
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_stats_flag(self):
        """Test --stats flag."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            result = await handler.handle_stats()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_tasks_flag(self):
        """Test --tasks flag."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            result = await handler.handle_tasks_list()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_text_generation_flag(self):
        """Test --text-generation flag."""
        try:
            from core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(budget=1.0, enable_ml=False, verbose=False)
            result = await orchestrator.process_task("Hello world", task_name="text-generation")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_chain_of_thought_flag(self):
        """Test --chain-of-thought flag."""
        try:
            from core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(budget=1.0, enable_ml=False, verbose=False)
            result = await orchestrator.process_task("Hello world", task_name="text-generation", chain_of_thought=True)
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_enable_ml_flag(self):
        """Test --enable-ml flag."""
        try:
            from core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(budget=1.0, enable_ml=True, verbose=False)
            result = await orchestrator.process_task("Hello world", task_name="text-generation")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_verbose_flag(self):
        """Test --verbose flag."""
        try:
            from core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(budget=1.0, enable_ml=False, verbose=True)
            result = await orchestrator.process_task("Hello world", task_name="text-generation")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_budget_flag(self):
        """Test --budget flag."""
        try:
            from core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(budget=5.0, enable_ml=False, verbose=False)
            result = await orchestrator.process_task("Hello world", task_name="text-generation")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_language_flag(self):
        """Test --language flag."""
        try:
            from core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(budget=1.0, enable_ml=False, verbose=False)
            result = await orchestrator.process_task("Hola mundo", task_name="text-generation", language="es")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_selection_strategy_flag(self):
        """Test --selection-strategy flag."""
        try:
            from core.enhanced_orchestrator import EnhancedOrchestrator
            orchestrator = EnhancedOrchestrator(budget=1.0, enable_ml=False, verbose=False)
            result = await orchestrator.process_task("Hello world", task_name="text-generation", selection_strategy="ensemble_methods")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_enhanced_orchestrator_flag(self):
        """Test enhanced orchestrator with various flags."""
        try:
            from core.enhanced_orchestrator import EnhancedOrchestrator
            orchestrator = EnhancedOrchestrator(budget=1.0, enable_ml=False, verbose=False)
            result = await orchestrator.process_task("Hello world", task_name="text-generation")
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_hyde_flags(self):
        """Test HYDE-related flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test HYDE demo
            result = await handler.handle_hyde_demo()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_analytics_flags(self):
        """Test analytics-related flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test analytics demo
            result = await handler.handle_analytics_demo()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_cache_flags(self):
        """Test cache-related flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test clear cache
            result = await handler.handle_clear_cache()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_model_ranking_flags(self):
        """Test model ranking flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test model ranking
            result = await handler.handle_model_ranking()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_decision_stats_flags(self):
        """Test decision stats flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test decision stats
            result = await handler.handle_decision_stats()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_performance_stats_flags(self):
        """Test performance stats flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test performance stats
            result = await handler.handle_performance_stats()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_cache_stats_flags(self):
        """Test cache stats flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test cache stats
            result = await handler.handle_cache_stats()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_novel_ai_stats_flags(self):
        """Test novel AI stats flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test novel AI stats
            result = await handler.handle_novel_ai_stats()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def test_model_recommendations_flags(self):
        """Test model recommendations flags."""
        try:
            from core.task_handler import ComprehensiveTaskHandler
            handler = ComprehensiveTaskHandler()
            # Test model recommendations
            result = await handler.handle_model_recommendations()
            return result.success
        except Exception as e:
            print(f"   Error: {e}")
            return False

    async def run_all_tests(self):
        """Run all flag tests."""
        print("🧪 HFOrchestra Direct Flag Testing Suite")
        print("=" * 50)
        
        # Define all tests
        tests = [
            ("--help", self.test_help_flag, "should import main module"),
            ("--stats", self.test_stats_flag, "should show statistics"),
            ("--tasks", self.test_tasks_flag, "should list tasks"),
            ("--text-generation", self.test_text_generation_flag, "should generate text"),
            ("--chain-of-thought", self.test_chain_of_thought_flag, "should enable chain-of-thought"),
            ("--enable-ml", self.test_enable_ml_flag, "should enable ML features"),
            ("--verbose", self.test_verbose_flag, "should enable verbose output"),
            ("--budget", self.test_budget_flag, "should set budget"),
            ("--language", self.test_language_flag, "should set language"),
            ("--selection-strategy", self.test_selection_strategy_flag, "should use selection strategy"),
            ("Enhanced Orchestrator", self.test_enhanced_orchestrator_flag, "should use enhanced orchestrator"),
            ("--demo-hyde", self.test_hyde_flags, "should run HYDE demo"),
            ("--analytics-demo", self.test_analytics_flags, "should run analytics demo"),
            ("--clearcache", self.test_cache_flags, "should clear cache"),
            ("--model-ranking", self.test_model_ranking_flags, "should show model ranking"),
            ("--decision-stats", self.test_decision_stats_flags, "should show decision stats"),
            ("--performance-stats", self.test_performance_stats_flags, "should show performance stats"),
            ("--cache-stats", self.test_cache_stats_flags, "should show cache stats"),
            ("--novel-ai-stats", self.test_novel_ai_stats_flags, "should show novel AI stats"),
            ("--model-recommendations", self.test_model_recommendations_flags, "should show model recommendations"),
        ]
        
        # Run all tests
        for flag_name, test_function, behavior in tests:
            await self.test_flag(flag_name, test_function, behavior)
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 DIRECT FLAG TESTING SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.passed_flags) + len(self.failed_flags)
        success_rate = (len(self.passed_flags) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {len(self.passed_flags)}")
        print(f"❌ Failed: {len(self.failed_flags)}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.failed_flags:
            print(f"\n❌ Failed Flags:")
            for flag in self.failed_flags:
                print(f"   - {flag}")
        
        if self.passed_flags:
            print(f"\n✅ Passed Flags:")
            for flag in self.passed_flags:
                print(f"   - {flag}")
        
        # Save results to file
        results = {
            "total_tests": total_tests,
            "passed": len(self.passed_flags),
            "failed": len(self.failed_flags),
            "success_rate": success_rate,
            "passed_flags": self.passed_flags,
            "failed_flags": self.failed_flags
        }
        
        with open("direct_flag_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Results saved to: direct_flag_test_results.json")

async def main():
    """Main test function."""
    tester = DirectFlagTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
