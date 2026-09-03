import re
import json

with open(r'D:\harfile\ModelFusion\.agents\explorer_2\tools_extracted.json', 'r', encoding='utf-8') as f:
    tools = json.load(f)

with open(r'D:\harfile\ModelFusion\crates\cli\src\main.rs', 'r', encoding='utf-8') as f:
    main_rs = f.read()

# Check Args struct
args_struct_start = main_rs.find('struct Args {')
args_struct_end = main_rs.find('}\n\n#[derive', args_struct_start)
if args_struct_end == -1:
    args_struct_end = main_rs.find('}\r\n\r\n#[derive', args_struct_start)
if args_struct_end == -1:
    args_struct_end = main_rs.find('}\n\nasync fn', args_struct_start)

args_struct_text = main_rs[args_struct_start:args_struct_end]

missing_in_args = []
for t in tools[30:]: # specialized tools 31-91
    name = t['name']
    rust_field = name # snake_case
    if f"{rust_field}: bool" not in args_struct_text and f"{rust_field}:" not in args_struct_text:
        missing_in_args.append(name)

print(f"Checked {len(tools[30:])} specialized tools against Args struct in main.rs:")
print(f"Missing in Args struct: {len(missing_in_args)}")
if missing_in_args:
    print(f"Missing list: {missing_in_args}")
else:
    print("ALL 61 specialized tools are defined in Args struct!")
