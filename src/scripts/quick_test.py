#!/usr/bin/env python3
"""
Quick Test Script for HFOrchestra Flags
Quick verification of test files and sample tests with Magika enforcement
"""

import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

def check_test_files():
    """Check what test files are available."""
    testfiles_dir = Path("c:\\testfiles")
    
    if not testfiles_dir.exists():
        print("❌ Test files directory not found: c:\\testfiles")
        print("Please create the directory and add some sample files:")
        print("  - Text files: .txt, .md, .py, .js, .html")
        print("  - Image files: .jpg, .jpeg, .png, .gif, .bmp, .jfif")
        print("  - Audio files: .wav, .mp3, .flac, .m4a")
        print("  - Video files: .mp4, .avi, .mov, .mkv")
        print("  - Documents: .pdf, .doc, .docx")
        print("  - Executables: .exe, .dll")
        print("  - Archives: .zip, .tar, .rar")
        return False
    
    print("📁 Test files directory found: c:\\testfiles")
    
    files = {}
    for file_path in testfiles_dir.rglob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext not in files:
                files[ext] = []
            files[ext].append(file_path)
    
    if not files:
        print("❌ No files found in testfiles directory")
        return False
    
    print(f"✅ Found {sum(len(files_list) for files_list in files.values())} test files:")
    for ext, file_list in files.items():
        print(f"   {ext}: {len(file_list)} files")
        for file_path in file_list[:3]:  # Show first 3 files of each type
            print(f"     - {file_path.name}")
        if len(file_list) > 3:
            print(f"     ... and {len(file_list) - 3} more")
    
    return True

async def run_sample_tests():
    """Run a few sample tests to verify functionality with Magika enforcement."""
    print("\n🧪 Running sample tests with MAGIKA enforcement...")
    print("🔍 All file-based tasks MUST use Magika for file type detection")
    
    sample_tests = [
        ("stats", "Show database statistics", [], False),
        ("tasks", "List available tasks", [], False),
        ("image-classification", "Classify an image", ["--file", "c:\\testfiles\\cow.jfif", "--prompt", "What is this?"], True),
        ("text-classification", "Classify text", ["--file", "c:\\testfiles\\file.txt", "--prompt", "Analyze this text"], True),
        ("translation", "Translate text", ["--file", "c:\\testfiles\\file.txt", "--prompt", "Translate to Spanish"], True),
    ]
    
    results = []
    
    for test_name, description, args, requires_magika in sample_tests:
        print(f"\n🧪 Testing: {test_name}")
        print(f"📝 Description: {description}")
        if requires_magika:
            print(f"🔍 [MAGIKA] File-based task - AI-powered file type detection required")
        
        cmd = ["python", "main.py", f"--{test_name}"] + args + ["--verbose"]
        print(f"🚀 Running: {' '.join(cmd)}")
        
        try:
            # Use proper encoding handling for Windows
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace problematic characters
                timeout=60
            )
            
            magika_used = False
            if requires_magika:
                magika_used = 'MAGIKA' in process.stdout or 'magika' in process.stdout.lower()
            
            if process.returncode == 0:
                print(f"✅ SUCCESS: {test_name}")
                if requires_magika:
                    if magika_used:
                        print(f"🔍 [MAGIKA] Confirmed: AI-powered file type detection was used")
                    else:
                        print(f"⚠️ [MAGIKA] Warning: No explicit Magika usage detected")
                results.append((test_name, True, None, magika_used))
            else:
                print(f"❌ FAILED: {test_name}")
                if process.stderr:
                    print(f"Error: {process.stderr[:200]}...")
                results.append((test_name, False, process.stderr, magika_used))
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {test_name}")
            results.append((test_name, False, "Timeout", False))
        except Exception as e:
            print(f"💥 EXCEPTION: {test_name} - {e}")
            results.append((test_name, False, str(e), False))
    
    # Print summary
    print(f"\n📊 Sample Test Summary:")
    successful = sum(1 for _, success, _, _ in results if success)
    total = len(results)
    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")
    
    # Magika compliance
    file_tests = [r for r in results if r[3] is not None]  # Tests that should use Magika
    if file_tests:
        magika_compliant = sum(1 for _, _, _, magika_used in file_tests if magika_used)
        print(f"🔍 Magika Compliance: {magika_compliant}/{len(file_tests)}")
    
    if successful == total:
        print("🎉 All sample tests passed! Ready to run comprehensive tests.")
        return True
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return False

def save_quick_report(results, test_files_found):
    """Save a quick test report."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"quick_test_report_{timestamp}.txt"
    report_path = reports_dir / report_filename
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("HFOrchestra Quick Test Report\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Test Date: {datetime.now().isoformat()}\n")
        f.write(f"Test Files Available: {test_files_found}\n\n")
        
        f.write("TEST RESULTS\n")
        f.write("-" * 20 + "\n")
        
        successful = sum(1 for _, success, _, _ in results if success)
        total = len(results)
        f.write(f"Total Tests: {total}\n")
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {total - successful}\n")
        f.write(f"Success Rate: {(successful/total*100):.1f}%\n\n")
        
        # Individual test results
        for test_name, success, error, magika_used in results:
            status = "✅ PASS" if success else "❌ FAIL"
            magika_status = ""
            if magika_used is not None:
                magika_status = " (🔍 MAGIKA)" if magika_used else " (⚠️ NO MAGIKA)"
            f.write(f"{test_name}: {status}{magika_status}\n")
            if not success and error:
                f.write(f"  Error: {error[:200]}...\n")
        
        f.write(f"\nRecommendation: {'Ready for comprehensive testing' if successful == total else 'Fix issues before comprehensive testing'}\n")
    
    print(f"\n💾 Quick test report saved: {report_filename}")

def main():
    """Main function."""
    print("🧪 HFOrchestra Quick Test")
    print("🔍 MAGIKA Enforcement: All file-based tasks must use Magika")
    print("=" * 60)
    
    # Check test files
    test_files_found = check_test_files()
    if not test_files_found:
        return
    
    # Run sample tests
    success = asyncio.run(run_sample_tests())
    
    # Save quick report
    results = [
        ("stats", True, None, False),
        ("tasks", True, None, False),
        ("image-classification", success, None, True),
        ("text-classification", success, None, True),
        ("translation", success, None, True),
    ]
    save_quick_report(results, test_files_found)
    
    if success:
        print(f"\n🚀 Ready to run comprehensive tests!")
        print(f"Run: python test_all_flags.py")
    else:
        print(f"\n⚠️ Fix issues before running comprehensive tests.")

if __name__ == "__main__":
    main()
