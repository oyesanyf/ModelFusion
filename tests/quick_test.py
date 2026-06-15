#!/usr/bin/env python3
"""
Quick Test - Individual Command Line Option Tester
Test one command line option at a time for rapid verification.
"""

import asyncio
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class QuickTester:
    """Quick tester for individual command line options."""
    
    OPTION_GROUPS = {
        "basic": [
            "--help",
            "--prompt 'What is AI?'",
            "--task 'Explain machine learning'",
            "--budget 5.0 --prompt 'Test'",
            "--verbose --prompt 'Verbose test'",
            "--language es --prompt 'Hola'",
        ],
        
        "database": [
            "--stats",
            "--tasks",
            "--tasks text",
            "--clearcache",
        ],
        
        "text": [
            "--text-classification --prompt 'I love this!'",
            "--sentiment --prompt 'Great movie!'",
            "--question-answering --prompt 'What is ML?'",
            "--summarization --prompt 'Long text here...'",
            "--translation --prompt 'Hello world'",
            "--ner --prompt 'John works at Google'",
        ],
        
        "security": [
            "--spam-detection --prompt 'WIN MONEY NOW!'",
            "--pii-detection --prompt 'Email: test@example.com'",
            "--malware-text-detection --prompt 'Suspicious code'",
        ],
        
        "advanced": [
            "--demo-hyde",
            "--search-query 'AI' --top-k 3",
            "--analytics-demo",
            "--model-ranking text-generation",
            "--decision-stats",
        ]
    }
    
    async def test_option(self, option_args: str, timeout: int = 30) -> dict:
        """Test a single command line option."""
        print(f"\n🧪 Testing: python main.py {option_args}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Parse arguments
            args = option_args.split()
            
            # Run command
            process = await asyncio.create_subprocess_exec(
                sys.executable, 'main.py', *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                exit_code = process.returncode
                
                # Decode output
                output = stdout.decode('utf-8', errors='ignore')
                error = stderr.decode('utf-8', errors='ignore')
                
            except asyncio.TimeoutError:
                process.kill()
                output = ""
                error = f"❌ Command timed out after {timeout} seconds"
                exit_code = -1
            
            execution_time = time.time() - start_time
            success = exit_code == 0
            
            # Display results
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{status} (Exit code: {exit_code}, Time: {execution_time:.2f}s)")
            
            if output:
                print("\n📄 OUTPUT:")
                print(output[:500] + ("..." if len(output) > 500 else ""))
            
            if error:
                print("\n⚠️ ERROR/WARNING:")
                print(error[:300] + ("..." if len(error) > 300 else ""))
            
            return {
                'success': success,
                'exit_code': exit_code,
                'execution_time': execution_time,
                'output': output,
                'error': error
            }
            
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            return {
                'success': False,
                'exit_code': -2,
                'execution_time': time.time() - start_time,
                'output': "",
                'error': str(e)
            }
    
    async def test_group(self, group_name: str):
        """Test all options in a group."""
        if group_name not in self.OPTION_GROUPS:
            print(f"❌ Unknown group: {group_name}")
            print(f"Available groups: {', '.join(self.OPTION_GROUPS.keys())}")
            return
        
        print(f"\n🎯 Testing {group_name.upper()} options group")
        print("=" * 60)
        
        options = self.OPTION_GROUPS[group_name]
        results = []
        
        for option in options:
            result = await self.test_option(option)
            results.append((option, result))
        
        # Summary
        print(f"\n📊 GROUP SUMMARY: {group_name.upper()}")
        print("-" * 30)
        passed = sum(1 for _, r in results if r['success'])
        total = len(results)
        print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for option, result in results:
            status = "✅" if result['success'] else "❌"
            print(f"  {status} {option}")
    
    def list_options(self):
        """List all available test options."""
        print("\n📋 Available Test Options:")
        print("=" * 40)
        
        for group, options in self.OPTION_GROUPS.items():
            print(f"\n🔸 {group.upper()} ({len(options)} options):")
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")
    
    async def interactive_mode(self):
        """Interactive testing mode."""
        print("\n🎮 Interactive Testing Mode")
        print("=" * 40)
        print("Commands:")
        print("  list           - Show all available options")
        print("  test <group>   - Test a group (basic, database, text, security, advanced)")
        print("  run <command>  - Test a specific command")
        print("  quit           - Exit")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if command == "quit":
                    break
                elif command == "list":
                    self.list_options()
                elif command.startswith("test "):
                    group = command[5:].strip()
                    await self.test_group(group)
                elif command.startswith("run "):
                    option = command[4:].strip()
                    await self.test_option(option)
                else:
                    print("❌ Unknown command. Type 'list' to see options.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                break


async def main():
    """Main entry point."""
    tester = QuickTester()
    
    if len(sys.argv) == 1:
        # Interactive mode
        await tester.interactive_mode()
    elif len(sys.argv) == 2:
        if sys.argv[1] == "list":
            tester.list_options()
        elif sys.argv[1] in tester.OPTION_GROUPS:
            await tester.test_group(sys.argv[1])
        else:
            print(f"❌ Unknown option: {sys.argv[1]}")
            print(f"Available: {', '.join(tester.OPTION_GROUPS.keys())}")
    else:
        # Test specific command
        option_args = " ".join(sys.argv[1:])
        await tester.test_option(option_args)


if __name__ == '__main__':
    asyncio.run(main())
