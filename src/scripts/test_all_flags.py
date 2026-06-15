#!/usr/bin/env python3
"""
Comprehensive Flag Testing Script for HFOrchestra

This script tests all command-line flags to ensure they are working correctly.
"""

import asyncio
import os
import sys
import subprocess
import json
from pathlib import Path

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class FlagTester:
    def __init__(self):
        self.results = {}
        self.failed_flags = []
        self.passed_flags = []
        
    async def test_flag(self, flag_name, command_args, expected_behavior="should not crash"):
        """Test a single flag."""
        print(f"🧪 Testing flag: {flag_name}")
        print(f"   Command: python main.py {' '.join(command_args)}")
        
        try:
            # Run the command with a timeout
            result = subprocess.run(
                ['python', 'main.py'] + command_args,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Check if the command ran successfully
            if result.returncode == 0:
                print(f"   ✅ PASS: {flag_name} - {expected_behavior}")
                self.passed_flags.append(flag_name)
                return True
            else:
                print(f"   ❌ FAIL: {flag_name} - Return code: {result.returncode}")
                print(f"   Error: {result.stderr[:200]}...")
                self.failed_flags.append(flag_name)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ TIMEOUT: {flag_name} - Command took too long")
            self.failed_flags.append(flag_name)
            return False
        except Exception as e:
            print(f"   💥 ERROR: {flag_name} - {str(e)}")
            self.failed_flags.append(flag_name)
            return False

    async def test_basic_flags(self):
        """Test basic system flags."""
        print("\n🔧 Testing Basic System Flags")
        print("=" * 40)
        
        basic_tests = [
            ("--help", ["--help"], "should show help"),
            ("--version", ["--version"], "should show version"),
            ("--verbose", ["--verbose", "--prompt", "test"], "should enable verbose output"),
            ("--debug", ["--debug", "--prompt", "test"], "should enable debug mode"),
            ("--budget", ["--budget", "5.0", "--prompt", "test"], "should set budget"),
            ("--language", ["--language", "es", "--prompt", "test"], "should set language"),
            ("--config", ["--config", "config/settings.json", "--prompt", "test"], "should use config file"),
        ]
        
        for flag_name, args, behavior in basic_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_task_flags(self):
        """Test task-specific flags."""
        print("\n📋 Testing Task Flags")
        print("=" * 40)
        
        task_tests = [
            ("--text-generation", ["--text-generation", "--prompt", "Hello world"], "should generate text"),
            ("--text-classification", ["--text-classification", "--prompt", "This is great"], "should classify text"),
            ("--summarization", ["--summarization", "--prompt", "Summarize this text"], "should summarize"),
            ("--translation", ["--translation", "--prompt", "Translate to Spanish"], "should translate"),
            ("--question-answering", ["--question-answering", "--prompt", "What is AI?"], "should answer questions"),
            ("--sentiment", ["--sentiment", "--prompt", "I love this"], "should analyze sentiment"),
            ("--ner", ["--ner", "--prompt", "John Smith works at Google"], "should extract entities"),
        ]
        
        for flag_name, args, behavior in task_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_enhancement_flags(self):
        """Test enhancement flags."""
        print("\n🚀 Testing Enhancement Flags")
        print("=" * 40)
        
        enhancement_tests = [
            ("--enable-ml", ["--enable-ml", "--prompt", "test"], "should enable ML features"),
            ("--chain-of-thought", ["--chain-of-thought", "--prompt", "test"], "should enable chain-of-thought"),
            ("--use-openai", ["--use-openai", "--prompt", "test"], "should use OpenAI models"),
            ("--score", ["--score", "--prompt", "test"], "should enable scoring"),
            ("--judge", ["--judge", "--prompt", "test"], "should enable LLM-as-judge"),
            ("--plan", ["--plan", "--prompt", "test"], "should enable planning"),
        ]
        
        for flag_name, args, behavior in enhancement_tests:
            await self.test_flag(flag_name, args, behavior)
    
    async def test_sinq_flags(self):
        """Test SINQ quantization flags."""
        print("\n🔧 Testing SINQ Quantization Flags")
        print("=" * 40)
        
        sinq_tests = [
            ("--sinq", ["--sinq", "--prompt", "test"], "should enable SINQ quantization"),
            ("--sinq-nbits", ["--sinq", "--sinq-nbits", "4", "--prompt", "test"], "should set SINQ bit-width"),
            ("--sinq-group-size", ["--sinq", "--sinq-group-size", "128", "--prompt", "test"], "should set SINQ group size"),
            ("--sinq-tiling-mode", ["--sinq", "--sinq-tiling-mode", "2D", "--prompt", "test"], "should set SINQ tiling mode"),
            ("--sinq-method", ["--sinq", "--sinq-method", "asinq", "--prompt", "test"], "should set SINQ method"),
        ]
        
        for flag_name, args, behavior in sinq_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_selection_strategy_flags(self):
        """Test model selection strategy flags."""
        print("\n🎯 Testing Selection Strategy Flags")
        print("=" * 40)
        
        strategy_tests = [
            ("--selection-strategy ensemble_methods", ["--selection-strategy", "ensemble_methods", "--prompt", "test"], "should use ensemble methods"),
            ("--selection-strategy multi_objective", ["--selection-strategy", "multi_objective", "--prompt", "test"], "should use multi-objective"),
            ("--selection-strategy cross_validation", ["--selection-strategy", "cross_validation", "--prompt", "test"], "should use cross-validation"),
        ]
        
        for flag_name, args, behavior in strategy_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_hyde_flags(self):
        """Test HYDE-related flags."""
        print("\n🔍 Testing HYDE Flags")
        print("=" * 40)
        
        hyde_tests = [
            ("--enable-hyde", ["--enable-hyde", "--prompt", "test"], "should enable HYDE"),
            ("--use-hyde", ["--use-hyde", "--prompt", "test"], "should use HYDE"),
            ("--hyde-variants", ["--hyde-variants", "--prompt", "test"], "should use HYDE variants"),
            ("--demo-hyde", ["--demo-hyde"], "should run HYDE demo"),
        ]
        
        for flag_name, args, behavior in hyde_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_innovation_flags(self):
        """Test innovation system flags."""
        print("\n💡 Testing Innovation Flags")
        print("=" * 40)
        
        innovation_tests = [
            ("--enable-innovations", ["--enable-innovations", "--prompt", "test"], "should enable innovations"),
            ("--workflow-optimization", ["--workflow-optimization", "--prompt", "test"], "should enable workflow optimization"),
            ("--semantic-analysis", ["--semantic-analysis", "--prompt", "test"], "should enable semantic analysis"),
            ("--temporal-tracking", ["--temporal-tracking", "--prompt", "test"], "should enable temporal tracking"),
            ("--predictive-mode", ["--predictive-mode", "--prompt", "test"], "should enable predictive mode"),
            ("--innovation-level", ["--innovation-level", "3", "--prompt", "test"], "should set innovation level"),
        ]
        
        for flag_name, args, behavior in innovation_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_data_analysis_flags(self):
        """Test data analysis flags."""
        print("\n📊 Testing Data Analysis Flags")
        print("=" * 40)
        
        # Create a test CSV file
        test_csv = "test_data.csv"
        with open(test_csv, "w") as f:
            f.write("name,age,city\nJohn,25,New York\nJane,30,Los Angeles\n")
        
        data_tests = [
            ("--data-analyst", ["--data-analyst", "--file", test_csv, "--prompt", "Find insights"], "should run data analyst"),
            ("--datanalyst", ["--datanalyst", "--file", test_csv, "--prompt", "Find insights"], "should run data analyst (alias)"),
            ("--jupyter", ["--jupyter"], "should launch Jupyter"),
            ("--export-pdf", ["--export-pdf", "--file", test_csv, "--prompt", "test"], "should export PDF"),
        ]
        
        for flag_name, args, behavior in data_tests:
            await self.test_flag(flag_name, args, behavior)
        
        # Clean up test file
        if os.path.exists(test_csv):
            os.remove(test_csv)

    async def test_system_flags(self):
        """Test system management flags."""
        print("\n⚙️ Testing System Management Flags")
        print("=" * 40)
        
        system_tests = [
            ("--stats", ["--stats"], "should show statistics"),
            ("--tasks", ["--tasks"], "should list tasks"),
            ("--update", ["--update"], "should update database"),
            ("--clearcache", ["--clearcache"], "should clear cache"),
            ("--analytics-demo", ["--analytics-demo"], "should run analytics demo"),
            ("--model-ranking", ["--model-ranking"], "should show model ranking"),
            ("--model-recommendations", ["--model-recommendations"], "should show recommendations"),
            ("--decision-stats", ["--decision-stats"], "should show decision stats"),
            ("--novel-ai-stats", ["--novel-ai-stats"], "should show novel AI stats"),
            ("--performance-stats", ["--performance-stats"], "should show performance stats"),
            ("--cache-stats", ["--cache-stats"], "should show cache stats"),
        ]
        
        for flag_name, args, behavior in system_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_device_flags(self):
        """Test device selection flags."""
        print("\n💻 Testing Device Flags")
        print("=" * 40)
        
        device_tests = [
            ("--cpu", ["--cpu", "--prompt", "test"], "should force CPU usage"),
            ("--gpu", ["--gpu", "--prompt", "test"], "should force GPU usage"),
        ]
        
        for flag_name, args, behavior in device_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_advanced_flags(self):
        """Test advanced decision science flags."""
        print("\n🧠 Testing Advanced Decision Science Flags")
        print("=" * 40)
        
        advanced_tests = [
            ("--delegation", ["--delegation", "--prompt", "test"], "should use delegation"),
            ("--recursion", ["--recursion", "--prompt", "test"], "should use recursion"),
            ("--real-options", ["--real-options", "--prompt", "test"], "should use real options"),
            ("--prompt-quality-scoring", ["--prompt-quality-scoring", "--prompt", "test"], "should score prompt quality"),
            ("--full", ["--full", "--prompt", "test"], "should enable full analysis"),
        ]
        
        for flag_name, args, behavior in advanced_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_security_flags(self):
        """Test security-related flags."""
        print("\n🔒 Testing Security Flags")
        print("=" * 40)
        
        security_tests = [
            ("--spam-detection", ["--spam-detection", "--prompt", "test"], "should detect spam"),
            ("--malware-text-detection", ["--malware-text-detection", "--prompt", "test"], "should detect malware text"),
            ("--phishing-detection", ["--phishing-detection", "--prompt", "test"], "should detect phishing"),
            ("--pii-detection", ["--pii-detection", "--prompt", "test"], "should detect PII"),
            ("--hate-speech-detection", ["--hate-speech-detection", "--prompt", "test"], "should detect hate speech"),
            ("--fake-news-detection", ["--fake-news-detection", "--prompt", "test"], "should detect fake news"),
        ]
        
        for flag_name, args, behavior in security_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_specialized_flags(self):
        """Test specialized domain flags."""
        print("\n🎯 Testing Specialized Domain Flags")
        print("=" * 40)
        
        specialized_tests = [
            ("--financial-ner", ["--financial-ner", "--prompt", "test"], "should extract financial entities"),
            ("--legal-ner", ["--legal-ner", "--prompt", "test"], "should extract legal entities"),
            ("--biomedical-ner", ["--biomedical-ner", "--prompt", "test"], "should extract biomedical entities"),
            ("--financial-sentiment-analysis", ["--financial-sentiment-analysis", "--prompt", "test"], "should analyze financial sentiment"),
            ("--emotion-detection", ["--emotion-detection", "--prompt", "test"], "should detect emotions"),
            ("--sarcasm-detection", ["--sarcasm-detection", "--prompt", "test"], "should detect sarcasm"),
            ("--bias-detection", ["--bias-detection", "--prompt", "test"], "should detect bias"),
        ]
        
        for flag_name, args, behavior in specialized_tests:
            await self.test_flag(flag_name, args, behavior)

    async def test_image_flags(self):
        """Test image processing flags."""
        print("\n🖼️ Testing Image Processing Flags")
        print("=" * 40)
        
        # Create a test image file (empty file for testing)
        test_image = "test_image.png"
        with open(test_image, "w") as f:
            f.write("fake image data")
        
        image_tests = [
            ("--image-classification", ["--image-classification", "--file", test_image, "--prompt", "What is this?"], "should classify image"),
            ("--object-detection", ["--object-detection", "--file", test_image, "--prompt", "What objects?"], "should detect objects"),
            ("--image-segmentation", ["--image-segmentation", "--file", test_image, "--prompt", "Segment this"], "should segment image"),
            ("--zero-shot-image-classification", ["--zero-shot-image-classification", "--file", test_image, "--prompt", "test"], "should do zero-shot classification"),
        ]
        
        for flag_name, args, behavior in image_tests:
            await self.test_flag(flag_name, args, behavior)
        
        # Clean up test file
        if os.path.exists(test_image):
            os.remove(test_image)

    async def test_audio_flags(self):
        """Test audio processing flags."""
        print("\n🎵 Testing Audio Processing Flags")
        print("=" * 40)
        
        # Create a test audio file (empty file for testing)
        test_audio = "test_audio.wav"
        with open(test_audio, "w") as f:
            f.write("fake audio data")
        
        audio_tests = [
            ("--automatic-speech-recognition", ["--automatic-speech-recognition", "--file", test_audio, "--prompt", "Transcribe this"], "should transcribe audio"),
            ("--audio-classification", ["--audio-classification", "--file", test_audio, "--prompt", "Classify this"], "should classify audio"),
            ("--voice-activity-detection", ["--voice-activity-detection", "--file", test_audio, "--prompt", "Detect voice"], "should detect voice activity"),
            ("--emotion-recognition", ["--emotion-recognition", "--file", test_audio, "--prompt", "Detect emotion"], "should recognize emotions"),
        ]
        
        for flag_name, args, behavior in audio_tests:
            await self.test_flag(flag_name, args, behavior)
        
        # Clean up test file
        if os.path.exists(test_audio):
            os.remove(test_audio)

    async def run_all_tests(self):
        """Run all flag tests."""
        print("🧪 HFOrchestra Flag Testing Suite")
        print("=" * 50)
        
        # Run all test categories
        await self.test_basic_flags()
        await self.test_task_flags()
        await self.test_enhancement_flags()
        await self.test_sinq_flags()
        await self.test_selection_strategy_flags()
        await self.test_hyde_flags()
        await self.test_innovation_flags()
        await self.test_data_analysis_flags()
        await self.test_system_flags()
        await self.test_device_flags()
        await self.test_advanced_flags()
        await self.test_security_flags()
        await self.test_specialized_flags()
        await self.test_image_flags()
        await self.test_audio_flags()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 FLAG TESTING SUMMARY")
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
        
        with open("flag_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Results saved to: flag_test_results.json")

async def main():
    """Main test function."""
    tester = FlagTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())