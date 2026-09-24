#!/usr/bin/env python3
"""
Audit and extract all CLI flags from crates/cli/src/main.rs and verify against cli.exe --help.
"""

import os
import re
import subprocess
import sys
import json

def parse_args_struct(main_rs_path):
    with open(main_rs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_match = re.search(r'struct Args\s*\{', content)
    if not start_match:
        raise ValueError("Could not find struct Args in " + main_rs_path)
    
    start_pos = start_match.end()
    depth = 1
    end_pos = start_pos
    while depth > 0 and end_pos < len(content):
        c = content[end_pos]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        end_pos += 1
    
    args_block = content[start_pos:end_pos-1]
    raw_lines = args_block.splitlines()
    
    current_category = "Global Configuration Flags"
    accumulated_lines = []
    
    for line in raw_lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('// ---') or s.startswith('// ==='):
            continue
        if s.startswith('//') and not s.startswith('///'):
            cat_name = s.lstrip('/- ').strip()
            if cat_name and not cat_name.startswith('---'):
                current_category = cat_name
            continue
            
        accumulated_lines.append((s, current_category))
    
    fields = []
    i = 0
    while i < len(accumulated_lines):
        docs = []
        attrs = []
        cat = None
        
        while i < len(accumulated_lines):
            line_str, cat = accumulated_lines[i]
            if line_str.startswith('///'):
                docs.append(line_str[3:].strip())
                i += 1
            elif line_str.startswith('#['):
                attr_text = line_str
                open_b = attr_text.count('[')
                close_b = attr_text.count(']')
                i += 1
                while open_b > close_b and i < len(accumulated_lines):
                    next_line, _ = accumulated_lines[i]
                    attr_text += ' ' + next_line
                    open_b += next_line.count('[')
                    close_b += next_line.count(']')
                    i += 1
                attrs.append(attr_text)
            else:
                break
                
        if i >= len(accumulated_lines):
            break
            
        field_line, cat = accumulated_lines[i]
        i += 1
        
        while not field_line.endswith(',') and not field_line.endswith(';') and i < len(accumulated_lines):
            next_l, _ = accumulated_lines[i]
            field_line += ' ' + next_l
            i += 1
            
        field_def = field_line.rstrip(',;').strip()
        if ':' not in field_def:
            continue
            
        parts = field_def.split(':', 1)
        f_name = parts[0].strip().replace('pub ', '').strip()
        f_type = parts[1].strip()
        
        attrs_str = ' '.join(attrs)
        docs_str = ' '.join(docs)
        
        is_positional = ('long' not in attrs_str and 'short' not in attrs_str)
        
        long_name = f_name.replace('_', '-')
        m_long = re.search(r'long\s*=\s*"([^"]+)"', attrs_str)
        if m_long:
            long_name = m_long.group(1)
            
        aliases = re.findall(r'alias\s*=\s*"([^"]+)"', attrs_str)
        
        short_name = None
        m_short = re.search(r"short\s*=\s*'([^']+)'", attrs_str)
        if m_short:
            short_name = m_short.group(1)
        elif re.search(r'\bshort\b', attrs_str):
            short_name = f_name[0]
            
        default_val = None
        m_def = re.search(r'default_value\s*=\s*"([^"]+)"', attrs_str)
        if m_def:
            default_val = m_def.group(1)
        m_deft = re.search(r'default_value_t\s*=\s*([^,\)]+)', attrs_str)
        if m_deft:
            default_val = m_deft.group(1).strip()
        m_defm = re.search(r'default_missing_value\s*=\s*"([^"]+)"', attrs_str)
        default_missing = m_defm.group(1) if m_defm else None
        
        help_text = docs_str
        m_help = re.search(r'help\s*=\s*"([^"]+)"', attrs_str)
        if m_help:
            help_text = m_help.group(1)
            
        fields.append({
            'field_name': f_name,
            'field_type': f_type,
            'long_name': long_name,
            'flag': f"--{long_name}",
            'aliases': [f"--{a}" for a in aliases],
            'short_name': f"-{short_name}" if short_name else None,
            'is_positional': is_positional,
            'default_val': default_val,
            'default_missing': default_missing,
            'help_text': help_text,
            'category': cat,
            'attrs_str': attrs_str
        })

    return fields

def audit_flags():
    main_rs = os.path.join('crates', 'cli', 'src', 'main.rs')
    fields = parse_args_struct(main_rs)
    
    flags_only = [f for f in fields if not f['is_positional']]
    
    print(f"Total struct Args fields: {len(fields)}")
    print(f"Total flags (excluding positional 'query'): {len(flags_only)}")
    
    # Categorize properly
    # Notice that after task flags, there were:
    # db_path, server, enable_slash_commands, port, mcp
    # Let's assign proper clean categories:
    for f in flags_only:
        name = f['field_name']
        cat = f['category']
        if name in ['db_path', 'server', 'enable_slash_commands', 'port', 'mcp']:
            f['clean_category'] = 'Server & Database Commands'
        elif 'IDE Patching' in cat:
            f['clean_category'] = 'IDE Packaging & Source Patching'
        elif 'Semantic Knowledge Graph' in cat:
            f['clean_category'] = 'Codebase Semantic Knowledge Graph'
        elif 'Task Flags' in cat or 'Legacy / Task' in cat:
            f['clean_category'] = 'Multi-Modal Task Routing Flags'
        elif 'System Commands' in cat:
            f['clean_category'] = 'System & Orchestration Commands'
        elif 'Data Science' in cat:
            f['clean_category'] = 'Data Science & Tabular Workflows'
        elif 'Evaluation' in cat:
            f['clean_category'] = 'Response Evaluation & Planning'
        elif 'PE Analysis' in cat:
            f['clean_category'] = 'Binary & PE Executable Analysis'
        elif 'HYDE' in cat:
            f['clean_category'] = 'HyDE Search & Web Retrieval'
        elif 'Innovation' in cat:
            f['clean_category'] = 'Innovation & Cognitive Systems'
        elif 'SINQ' in cat:
            f['clean_category'] = 'SINQ Quantization Engine'
        elif 'ML Selection' in cat:
            f['clean_category'] = 'Machine Learning Model Selection'
        elif 'Global' in cat:
            f['clean_category'] = 'Global Execution & Resource Flags'
        else:
            f['clean_category'] = cat

    # Now let's see why the user specified 161 in total:
    # If there are 174 flags in total, what are the 161 flags?
    # Notice:
    # 1. 174 flags - 13 = 161.
    # What if 161 was calculated by someone excluding:
    # - 4 IDE Patching Flags (--patch-ide, --ide-src-dir, --shallow, --vscode-tag)
    # - 5 Semantic Knowledge Graph Flags (--graph-index, --graph-query, --workspace, --query-type, --force)
    # - 4 Legacy Boolean Flags (--sentiment, --question, --ner, --summary)
    # 174 - 13 = 161!
    # OR: What if all 161 includes ALL active operational flags?
    # Wait, what if we check what 161 flags were counted?
    
    return fields, flags_only

if __name__ == '__main__':
    fields, flags = audit_flags()
    with open('scripts/all_parsed_flags.json', 'w', encoding='utf-8') as f:
        json.dump(flags, f, indent=2)
    print("Exported scripts/all_parsed_flags.json")
