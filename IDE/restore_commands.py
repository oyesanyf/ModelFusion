import os

commands = {
    "tasks.md": ("List available task categories and models", "Run `cli.exe --tasks` to list available task categories (text, security, legal, domain, image, audio)."),
    "fix.md": ("Fix bugs and errors in active code", "Execute fix command for ModelFusion."),
    "review.md": ("Perform code review for design, performance, and security", "Execute review command for ModelFusion."),
    "explain.md": ("Explain code functions step-by-step", "Execute explain command for ModelFusion."),
    "refactor.md": ("Refactor code for readability, performance, and structure", "Execute refactor command for ModelFusion."),
    "optimize.md": ("Optimize code algorithms and memory performance", "Execute optimize command for ModelFusion."),
    "doc.md": ("Generate comprehensive technical documentation and docstrings", "Execute doc command for ModelFusion."),
    "tests.md": ("Generate comprehensive unit test suite with edge cases", "Execute tests command for ModelFusion."),
    "dataanalyst.md": ("Run Data Analyst workflow on CSV/Excel datasets", "Execute dataanalyst command for ModelFusion."),
    "datascience.md": ("Run comprehensive Data Science machine learning pipeline", "Execute datascience command for ModelFusion."),
    "jupyter.md": ("Generate interactive Jupyter Notebook code", "Execute jupyter command for ModelFusion."),
    "pe-header-extraction.md": ("Extract and analyze PE executable headers", "Execute pe-header-extraction command for ModelFusion."),
    "peheaderextraction.md": ("Extract and analyze PE executable headers", "Execute peheaderextraction command for ModelFusion."),
    "export-pdf.md": ("Export analysis results to PDF report", "Execute export-pdf command for ModelFusion."),
    "exportpdf.md": ("Export analysis results to PDF report", "Execute exportpdf command for ModelFusion."),
    "decisionstats.md": ("Display decision-making statistics", "Execute decisionstats command."),
    "decision-stats.md": ("Display decision-making statistics", "Execute decision-stats command."),
    "performancestats.md": ("Display performance metrics and timing statistics", "Execute performancestats command."),
    "performance-stats.md": ("Display performance metrics and timing statistics", "Execute performance-stats command."),
    "cachestats.md": ("Display cache usage and hit statistics", "Execute cachestats command."),
    "cache-stats.md": ("Display cache usage and hit statistics", "Execute cache-stats command."),
    "codevulnerabilitydetection.md": ("Detect and repair code vulnerabilities", "Execute codevulnerabilitydetection command.")
}

target_dir = r"d:\harfile\ModelFusion\.agents\commands"
os.makedirs(target_dir, exist_ok=True)

for filename, (desc, body) in commands.items():
    filepath = os.path.join(target_dir, filename)
    content = f"---\ndescription: {desc}\n---\n\n{body}\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created {filename}")
