#!/usr/bin/env python3
"""
Script to replace all instances of sagamu_llm_orhcestrator.py with HuggingFace_orhcestrator.py
"""

def replace_script_names():
    """Replace all instances of the old script name with the new one."""
    
    # Read the file
    with open('HuggingFace_orhcestrator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count occurrences
    old_count = content.count('sagamu_llm_orhcestrator.py')
    print(f"Found {old_count} instances of 'sagamu_llm_orhcestrator.py'")
    
    # Replace all instances
    new_content = content.replace('sagamu_llm_orhcestrator.py', 'HuggingFace_orhcestrator.py')
    
    # Count new occurrences
    new_count = new_content.count('HuggingFace_orhcestrator.py')
    print(f"Replaced with {new_count} instances of 'HuggingFace_orhcestrator.py'")
    
    # Write back to file
    with open('HuggingFace_orhcestrator.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully replaced all script name references!")
    return True

if __name__ == "__main__":
    replace_script_names() 