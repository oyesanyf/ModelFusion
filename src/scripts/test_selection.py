import sys
import os
import shutil
import time

# Add src to path just in case
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    import hforchestra.core.enhanced_model_selector as ems
    print(f"DEBUG: Loaded module from {ems.__file__}")
    from hforchestra.core.enhanced_model_selector import EnhancedModelSelector, SelectionStrategy, ModelCandidate
except ImportError:
    print("Could not import hforchestra. Ensure you are running from project root.")
    sys.exit(1)

def main():
    print("🔍 Testing Enhanced Model Selection Logic (DEBUG MODE)...")
    
    # Locate DB
    source_db = "src/db/hf_models_recovered.db"
    if not os.path.exists(source_db):
        source_db = "src/db/hf_models.db"
    
    if not os.path.exists(source_db):
        print("❌ No valid database found.")
        return

    # Copy to temp to avoid lock
    temp_db = "temp_test_db.db"
    try:
        shutil.copy2(source_db, temp_db)
        print(f"📂 Copied {source_db} to {temp_db} for testing")
    except Exception as e:
        print(f"⚠️ Could not copy DB: {e}. Trying original...")
        temp_db = source_db

    try:
        selector = EnhancedModelSelector(db_path=temp_db)
        
        task = "text-generation"
        print(f"\n🧠 Selecting best model for task: '{task}'")
        
        # Check ModelCandidate attributes directly
        c = ModelCandidate(
            model_id="test", pipeline_tag="test", author="test", library_name="test",
            downloads=0, likes=0, decision_score=0, capability_score=0, efficiency_score=0,
            popularity_score=0, size_mb=0, license="mit", base_model="test", datasets="",
            metrics="", widget_data="", inference_info="", popularity_score_normalized=0,
            engagement_score=0, lightweight_score=0, task_match_score=0
        )
        print(f"DEBUG: ModelCandidate attributes: {dir(c)}")
        has_freshness = hasattr(c, 'freshness_score')
        print(f"DEBUG: Has freshness_score? {has_freshness}")
        
        result = selector.select_best_model(
            task_name=task,
            prompt="Write a python code",
            strategy=SelectionStrategy.MULTI_OBJECTIVE
        )
        
        best = result.best_model
        print("\n🏆 WINNER:")
        print(f"  ID: {best.model_id}")
        print(f"  Reasoning: {result.reasoning}")
        
        if has_freshness:
            print(f"  Detailed Stats: Freshness={best.freshness_score:.2f}")
        else:
            print("  Detailed Stats: (freshness missing)")
        
    except Exception as e:
        print(f"❌ Selection failed: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    if temp_db != source_db and os.path.exists(temp_db):
        try:
            os.remove(temp_db)
        except:
            pass

if __name__ == "__main__":
    main()
