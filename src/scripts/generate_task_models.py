#!/usr/bin/env python3
"""
Dynamic Task Models Generator Script
Automatically generates task_models.json from the database with the best models for each task.
"""

import sys
import os
from pathlib import Path

# Add config directory to path
sys.path.append('config')

def main():
    """Generate dynamic task models from database."""
    print("🚀 Dynamic Task Models Generator")
    print("=" * 50)
    
    # Check if database exists
    db_path = Path("db/hf_models.db")
    if not db_path.exists():
        print("❌ Database not found: db/hf_models.db")
        print("💡 Please run the model discovery first to populate the database")
        return False
    
    try:
        # Import and run the dynamic generator
        from config.dynamic_task_generator import DynamicTaskGenerator
        
        generator = DynamicTaskGenerator()
        success = generator.run()
        
        if success:
            print("\n✅ Success! task_models.json has been generated dynamically from the database.")
            print("📊 The file now contains:")
            print("   • Best models for each task (ranked by downloads & likes)")
            print("   • Alternative models for fallback")
            print("   • Dynamic metadata and scores")
            print("   • No hardcoded configurations")
            print("\n🔄 The system will now automatically use the best models for each --prompt")
            return True
        else:
            print("\n❌ Failed to generate task models")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure the dynamic_task_generator.py file exists in the config directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 