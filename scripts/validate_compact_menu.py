compact_menu = {
    "Classification & Taxonomy": [
        ("Content Moderation", "@agent moderation text-moderation ", "tool_koalaai_text_moderation", "🚨", "@moderation"),
        ("Emotion Detection", "@agent sentiment distilbert-base-uncased-emotion ", "tool_distilbert_emotion", "🎭", "@emotion"),
        ("Fact Verification", "@agent classify deberta-v3-base-mnli-fever-anli ", "tool_deberta_v3_mnli_fever_anli", "🛡️", "@deberta-fever"),
        ("Finance Classifier", "@agent topic finbert ", "tool_finbert_classifier", "📈", "@finbert-cls"),
        ("Fine Emotions", "@agent sentiment roberta-base-go_emotions ", "tool_roberta_go_emotions", "💬", "@go-emotions"),
        ("High-Precision Match", "@agent classify nli-deberta-v3-base ", "tool_nli_deberta_v3_base", "🔀", "@deberta-nli"),
        ("Long Document Match", "@agent topic longformer-base-4096 ", "tool_longformer_base_4096", "📜", "@longformer"),
        ("Quick Topic Labeler", "@agent classify distilbart-mnli-12-3 ", "tool_distilbart_mnli_12_3", "⚡", "@distilbart-mnli"),
        ("Sentiment (Pos/Neg)", "@agent sentiment distilbert-base-uncased-finetuned-sst-2-english ", "tool_distilbert_sst2", "👍", "@sst2"),
        ("Social Sentiment", "@agent sentiment twitter-roberta-base-sentiment-latest ", "tool_twitter_roberta_sentiment", "🐦", "@twitter-sentiment"),
        ("Toxicity Detector", "@agent moderation toxic-bert ", "tool_toxic_bert", "☣️", "@toxic-bert"),
        ("Zero-Shot Classifier", "@agent classify bart-large-mnli ", "tool_bart_large_mnli", "🎯", "@bart-mnli"),
    ],
    "Code & Security": [
        ("Audit Code Security", "@agent security ", "tool_vuln_detection", "🛡️", "@security"),
        ("Code Architecture", "@agent graph-index ", "tool_graph_index", "🕸️", "@graph"),
    ],
    "Computer Use & OS Automation": [
        ("Autonomous Agent", "@agent computer-use ", "tool_computer_use", "🖥️", "@computer-use"),
        ("Exam Solver", "@agent exam-solver ", "tool_exam_solver", "📝", "@exam-solver"),
        ("Flight Booking", "@agent ticket-booking ", "tool_ticket_booking", "🎟️", "@ticket-booking"),
        ("Keyboard & Type", "@agent desktop-type ", "tool_desktop_type", "⌨️", "@type"),
        ("Map & Directions", "@agent map-directions ", "tool_map_directions", "🧭", "@map-directions"),
        ("Mouse & Click", "@agent desktop-click ", "tool_desktop_click", "🖱️", "@click"),
        ("Price Comparison", "@agent shopping ", "tool_shopping", "🛒", "@shopping"),
        ("Screen Perception", "@agent screen-grounding ", "tool_screen_grounding", "👁️", "@screen"),
        ("UI-TARS Agent", "@agent ui-tars ", "tool_ui_tars", "🤖", "@ui-tars"),
        ("Window Scroll", "@agent desktop-scroll ", "tool_desktop_scroll", "📜", "@scroll"),
    ],
    "Data & Spreadsheets (CSV/Excel)": [
        ("Automated ML", "@agent acdso ", "tool_acdso", "📊", "@acdso"),
        ("Data Insights", "@agent dataanalyst ", "tool_dataanalyst", "🔬", "@dataanalyst"),
        ("Data Science Flow", "@agent datascience ", "tool_datascience", "📈", "@datascience"),
        ("Decision Optimizer", "@agent decision ", "tool_decision", "⚖️", "@decision"),
        ("Predict Outcome", "@agent predict ", "tool_predict", "🎯", "@predict"),
        ("Time-Series Forecast", "@agent timeseries ", "tool_timeseries", "⏳", "@timeseries"),
    ],
    "Finance & Markets": [
        ("Corporate ESG", "@agent finbert-esg ", "tool_finbert_esg", "🌱", "@finbert-esg"),
        ("Earnings Call Tone", "@agent finbert-tone ", "tool_finbert_tone", "🎙️", "@finbert-tone"),
        ("Financial Advisory", "@agent finance-llm ", "tool_finance_llm", "💼", "@finance-llm"),
        ("Financial Forecast", "@agent chronos ", "tool_chronos", "⏳", "@chronos"),
        ("Financial News Mood", "@agent finbert ", "tool_finbert", "📊", "@finbert"),
        ("Institutional Fund", "@agent qwen-finance ", "tool_qwen_finance", "🏢", "@qwen-finance"),
        ("Market Modeling", "@agent patchtst ", "tool_patchtst", "📉", "@patchtst"),
        ("SEC Filing Analyst", "@agent llama-fin ", "tool_llama_fin", "🦙", "@llama-fin"),
        ("Stock Trend AI", "@agent fingpt ", "tool_fingpt", "🔮", "@fingpt"),
    ],
    "Images & Vision": [
        ("Ask Image (VQA)", "@agent vqa ", "tool_vqa", "❓", "@vqa"),
        ("Detect Objects", "@agent detect ", "tool_detect", "📦", "@detect"),
        ("Generate Image", "@agent image ", "tool_image", "🎨", "@image"),
        ("Identify Image", "@agent classify ", "tool_classify", "🏷️", "@classify"),
        ("Inspect Image", "@agent vision ", "tool_vision", "👁️", "@vision"),
        ("Video Analysis", "@agent video ", "tool_video", "🎬", "@video"),
    ],
    "Inspect Windows Apps (.EXE / .DLL)": [
        ("Inspect PE File", "@agent pe ", "tool_pe", "🔬", "@pe"),
    ],
    "Legal & Compliance": [
        ("Case Law & Precedent", "@agent lawma ", "tool_lawma", "🦙", "@lawma"),
        ("Contract Review", "@agent cuad ", "tool_cuad", "📜", "@cuad"),
        ("Document Classifier", "@agent legal-bert ", "tool_legal_bert", "⚖️", "@legal-bert"),
        ("Interactive Legal", "@agent law-chat ", "tool_law_chat", "💬", "@law-chat"),
        ("Legal Counsel", "@agent saul ", "tool_saul", "⚡", "@saul"),
        ("Multi-Page Contracts", "@agent longformer ", "tool_legal_longformer", "📑", "@longformer"),
        ("Regulatory Search", "@agent pile-of-law ", "tool_pile_of_law", "🏛️", "@pile-of-law"),
        ("Statutory Briefs", "@agent law-llm ", "tool_law_llm", "📚", "@law-llm"),
    ],
    "Planning & Deep Thinking": [
        ("Deep Reasoning", "@agent boost ", "tool_boost", "🚀", "@boost"),
        ("Goal Orchestrator", "@agent goal ", "tool_goal", "🎯", "@goal"),
        ("Interview & Clarify", "@agent grill-me ", "tool_grill_me", "🔥", "@grill-me"),
        ("Self-Correct Loop", "@agent loop ", "tool_loop", "🔄", "@loop"),
        ("Structured Plan", "@agent plan ", "tool_plan", "📐", "@plan"),
    ],
    "Science & Discovery": [
        ("Atmospheric Weather", "@agent aurora ", "tool_aurora", "🌦️", "@aurora"),
        ("Biomedical Science", "@agent scibert ", "tool_scibert", "📄", "@scibert"),
        ("Chemical Properties", "@agent chemberta ", "tool_chemberta", "🧪", "@chemberta"),
        ("Chemical Structure", "@agent smi-ted ", "tool_smi_ted", "⚗️", "@smi-ted"),
        ("Climate Risk", "@agent climatebert ", "tool_climatebert", "🌡️", "@climatebert"),
        ("DNA & RNA Genomics", "@agent nucleotide ", "tool_nucleotide", "🧬", "@nucleotide"),
        ("Earth Satellite AI", "@agent prithvi ", "tool_prithvi", "🛰️", "@prithvi"),
        ("Gene Modeling", "@agent geneformer ", "tool_geneformer", "🧫", "@geneformer"),
        ("Global Climate", "@agent climax ", "tool_climax", "🌪️", "@climax"),
        ("Materials Science", "@agent matscibert ", "tool_matscibert", "💎", "@matscibert"),
        ("Molecular Drugs", "@agent molformer ", "tool_molformer", "💊", "@molformer"),
        ("Molecular Graphs", "@agent mhg-ged ", "tool_mhg_ged", "🕸️", "@mhg-ged"),
        ("Multimodal Science", "@agent s1-omni ", "tool_s1_omni", "🔭", "@s1-omni"),
        ("Protein 3D Folding", "@agent esmfold ", "tool_esmfold", "🔬", "@esmfold"),
        ("Protein Biology", "@agent esm3 ", "tool_esm3", "✨", "@esm3"),
        ("Protein Sequences", "@agent esm2 ", "tool_esm2", "🧬", "@esm2"),
        ("Robust Chemistry", "@agent selfies-ted ", "tool_selfies_ted", "🔬", "@selfies-ted"),
        ("Scientific Knowledge", "@agent galactica ", "tool_galactica", "🌌", "@galactica"),
        ("Scientific Papers", "@agent scholarbert ", "tool_scholarbert", "📖", "@scholarbert"),
        ("Whole-Genome AI", "@agent evo ", "tool_evo", "🧬", "@evo"),
    ],
    "Utilities & System": [
        ("Active AI Model", "@agent model ", "tool_model", "🤖", "@model"),
        ("Audit Menu Suite", "@agent audit-menus ", "tool_audit_menus", "🧪", "@audit-menus"),
        ("Benchmark System", "@agent benchmark ", "tool_benchmark", "⚡", "@benchmark"),
        ("Catalog Database", "@agent db-rebuild ", "tool_db_rebuild", "🛠️", "@db-rebuild"),
        ("Clean Stale Cache", "@agent db-prune ", "tool_db_prune", "🗑️", "@db-prune"),
        ("Database Integrity", "@agent db-check ", "tool_db_check", "🔍", "@db-check"),
        ("Export Transcript", "@agent export ", "tool_export", "📥", "@export"),
        ("Full 2M+ Registry", "@agent updatedb ", "tool_updatedb", "🌐", "@updatedb"),
        ("Hardware & VRAM", "@agent sys-info ", "tool_sys_info", "💻", "@sys-info"),
        ("Help & Docs", "@agent help ", "tool_help", "💡", "@help"),
        ("Optimize Database", "@agent db-vacuum ", "tool_db_vacuum", "🧹", "@db-vacuum"),
        ("Update Top Models", "@agent update ", "tool_update", "⚡", "@update"),
    ],
    "Voice & Audio": [
        ("Audio Recognition", "@agent audio ", "tool_audio", "🎵", "@audio"),
        ("Speech to Text", "@agent asr ", "tool_asr", "🎙️", "@asr"),
        ("Text to Speech", "@agent tts ", "tool_tts", "🔊", "@tts"),
    ],
    "Web Research & Automation": [
        ("Academic Papers", "@agent arxiv ", "tool_arxiv", "📚", "@arxiv"),
        ("Deep Web Research", "@agent research ", "tool_research", "🔍", "@research"),
        ("Encyclopedia Wiki", "@agent wiki ", "tool_wiki", "📖", "@wiki"),
        ("Page Summarizer", "@agent summarize ", "tool_summarize", "📑", "@summarize"),
        ("Visual Grounding", "@agent markers ", "tool_markers", "🎯", "@markers"),
        ("Web Browser", "@agent browser ", "tool_browser", "🌐", "@browser"),
    ],
    "Writing & Editing": [
        ("AI Watermark", "@agent watermark ", "tool_watermark", "🔍", "@watermark"),
        ("Book Outlining", "@agent outline ", "tool_outline", "📖", "@outline"),
        ("Humanize Text", "@agent humanize ", "tool_humanize", "✍️", "@humanize"),
        ("Style Transfer", "@agent style ", "tool_style", "🎨", "@style"),
        ("Text Translation", "@agent translate ", "tool_translate", "🌐", "@translate"),
        ("Writing Boost", "@agent boost ", "tool_boost", "🚀", "@boost"),
    ],
}

max_len = 0
longest_name = ""
total = 0
all_sorted = True

for cat, tools in compact_menu.items():
    total += len(tools)
    labels = [t[0] for t in tools]
    exp = sorted(labels, key=str.casefold)
    if labels != exp:
        print(f"FAILED SORT: {cat}")
        for a, b in zip(labels, exp):
            print(f"  {a} vs {b}")
        all_sorted = False
    for l in labels:
        if len(l) > max_len:
            max_len = len(l)
            longest_name = l

print(f"Total tools: {total}")
print(f"Max label length: {max_len} chars ('{longest_name}')")
if all_sorted and total == 106 and max_len <= 20:
    print("SUCCESS: ALL 106 COMPACT NAMES ARE STRICTLY <= 20 CHARS AND 100% SORTED A-Z!")
else:
    print("FAILED VALIDATION")
