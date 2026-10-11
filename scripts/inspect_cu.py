with open('browser/ui/index.html', encoding='utf-8') as f:
    for line in f:
        if 'data-category="computer_use"' in line and '<button' in line:
            print(line.strip())
