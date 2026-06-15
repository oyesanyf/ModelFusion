import sys
import os
import inspect

# Ensure we use the path we expect
current = os.getcwd()
print(f"CWD: {current}")
# Use absolute path to src
src_path = os.path.join(current, 'src')
print(f"Adding to path: {src_path}")
sys.path.insert(0, src_path)

try:
    import hforchestra.core.enhanced_model_selector as ems
    print(f"Loaded Module File: {ems.__file__}")
    
    from hforchestra.core.enhanced_model_selector import ModelCandidate
    
    # Check if 'freshness_score' is in the fields
    if hasattr(ModelCandidate, '__dataclass_fields__'):
        fields = list(ModelCandidate.__dataclass_fields__.keys())
        print(f"ModelCandidate Fields: {fields}")
        
        if 'freshness_score' in fields:
            print("✅ VERIFIED: freshness_score is present in ModelCandidate.")
        else:
            print("❌ FAILURE: freshness_score is MISSING from ModelCandidate.")
            
            # Print content of file on disk to debug
            try:
                with open(ems.__file__, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"File content length: {len(content)}")
                    if "freshness_score" in content:
                        print("Context: File on disk HAS 'freshness_score'.")
                    else:
                        print("Context: File on disk MISING 'freshness_score'.")
            except Exception as e:
                print(f"Could not read module file: {e}")
            
    else:
        print("ModelCandidate is not a dataclass?")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
