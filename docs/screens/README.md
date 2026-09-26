# HugOS Browser & ModelFusion Interactive Screens

This directory contains the standalone interactive UI screens, prototypes, and Generative UI widgets built for the **ModelFusion / HugOS Browser** ecosystem.

## 📱 Interactive Screens Catalog

| Screen File | Description | Key Features |
| :--- | :--- | :--- |
| [**`hugos_aligned_chatgpt_widget.html`**](hugos_aligned_chatgpt_widget.html) | Aligned ChatGPT Generative UI Widget | Strictly centered 768px reading column, right-aligned user bubble, ModelFusion Auto consensus default, 5-theme switcher (White, Dark, Obsidian, Midnight, Warm). |
| [**`hugos_chatgpt_perfect_ui.html`**](hugos_chatgpt_perfect_ui.html) | Standalone ChatGPT-Style Simulator | 260px docked sidebar, 768px reading column, floating bottom input pill (`+`, `↑`), suggestion chips, zero cloud dependencies. |
| [**`hugos_chatgpt_browser_ui.html`**](hugos_chatgpt_browser_ui.html) | Full ChatGPT Browser Portal Mockup | Clean hero view *"Where should we begin?"*, full-width omnibox, quick tools, 5-theme switching, and live streaming simulation. |
| [**`hugos_browser_interface.html`**](hugos_browser_interface.html) | Full HugOS Intelligent Browser UI | Multi-pane browser with integrated CDP remote debugging port (9222), Set-of-Mark visual tagging, ACDSO AutoML trigger, and dual webview/terminal split. |
| [**`ModelFusion_Interactive_Docs.html`**](ModelFusion_Interactive_Docs.html) | Interactive 170-Flag CLI Documentation Portal | Live searchable and filterable database of all 170 Master CLI flags, subcommands, and concrete syntax examples. |
| [**`dashboard_widget.html`**](dashboard_widget.html) | ModelFusion Hardware Dashboard Widget | Runtime available RAM/VRAM monitor, dynamic model tier sizing visualizer, and local Ollama daemon status. |

---

## 🎨 Theme Matrix

All screens adhere to the 5 standard HugOS themes matching modern LLM environments:
- 🔆 **White**: Pure clean light theme with high contrast borders
- 🌑 **Dark**: Official ChatGPT charcoal palette (`#212121` background, `#2f2f2f` bubbles)
- ⬛ **Obsidian**: Pure OLED black (`#000000` background)
- 🌌 **Midnight**: Deep dark navy (`#090d16` background, `#1e293b` surfaces)
- 📜 **Warm**: Sepia/cream tone (`#fbf8f3` background, `#ede4d4` surfaces)

---

## 🚀 How to Run Locally

You can open any of these files directly in any web browser:
```bash
# Open in default browser (Windows)
start docs/screens/hugos_aligned_chatgpt_widget.html
start docs/screens/hugos_chatgpt_perfect_ui.html
start docs/screens/ModelFusion_Interactive_Docs.html
```
Or view them served via the ModelFusion Master CLI on port 5000:
```bash
cli.exe --browser
```
