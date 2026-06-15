#!/usr/bin/env python3
"""
Check Update Status Script
Quick utility to check the status of the HFOrchestra database update process.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.comprehensive_model_populator import ComprehensiveHFModelPopulator
    from core.task_handler import ComprehensiveTaskHandler
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running this from the correct directory")
    sys.exit(1)

def check_status():
    """Check the current update status."""
    print("🔍 Checking HFOrchestra Database Update Status...")
    print("=" * 60)
    
    # Initialize populator
    populator = ComprehensiveHFModelPopulator()
    
    # Get status
    status = populator.get_update_status()
    
    print(f"📊 Total Models: {status['total_models']:,}")
    print(f"🎯 Status: {status['status'].upper()}")
    print(f"🕒 Last Update: {status['last_update'] or 'Unknown'}")
    print(f"✅ Complete: {'Yes' if status['is_complete'] else 'No'}")
    
    if status['top_models']:
        print("\n🏆 Top Models by Downloads:")
        for i, (model_id, downloads, likes) in enumerate(status['top_models'], 1):
            print(f"   {i}. {model_id}")
            print(f"      Downloads: {downloads:,} | Likes: {likes}")
    
    print("\n" + "=" * 60)
    
    if status['is_complete']:
        print("✅ Database update is complete and ready for use!")
        print("💡 You can now use: python main.py --stats")
        print("💡 Or: python main.py --tasks")
    elif status['total_models'] > 0:
        print("🔄 Database update is in progress...")
        print(f"📈 {status['total_models']:,} models processed so far")
        print("💡 The update process is still running in the background")
    else:
        print("❌ No models found in database")
        print("💡 Run: python main.py --update to start the update process")
    
    return status['is_complete']

if __name__ == "__main__":
    try:
        check_status()
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        sys.exit(1)
