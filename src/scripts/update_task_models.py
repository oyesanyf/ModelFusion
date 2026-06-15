#!/usr/bin/env python3
"""
Task Models Updater
Updates task_models.json from database when --update flag is used
"""

import sys
import os
import argparse
from pathlib import Path

def update_task_models():
    """Update task_models.json from database."""
    try:
        print("🔄 Updating task_models.json from database...")
        
        # Import and run the enhanced dynamic generator
        from enhanced_dynamic_generator import EnhancedDynamicTaskGenerator
        
        generator = EnhancedDynamicTaskGenerator()
        success = generator.run()
        
        if success:
            print("✅ Task models updated successfully!")
            return True
        else:
            print("❌ Failed to update task models")
            return False
            
    except Exception as e:
        print(f"❌ Error updating task models: {e}")
        return False

def main():
    """Main function for updating task models."""
    parser = argparse.ArgumentParser(description='Update task_models.json from database')
    parser.add_argument('--update', action='store_true', help='Update task_models.json from database')
    parser.add_argument('--force', action='store_true', help='Force update even if file exists')
    
    args = parser.parse_args()
    
    if args.update:
        print("🚀 Starting task models update...")
        success = update_task_models()
        
        if success:
            print("✅ Update completed successfully!")
            return 0
        else:
            print("❌ Update failed!")
            return 1
    else:
        print("Usage: python update_task_models.py --update")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 