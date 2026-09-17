# Dual-Model AI Terminal Assistant

A smart, terminal-based AI assistant that automatically routes your prompts to the best model for the job—costing **$0.00** by utilizing OpenRouter's free tiers.

- **Coding Tasks** automatically go to **Poolside's Laguna S 2.1**. It acts as a Senior Developer using the "Ponytail Principle"—writing minimal, targeted code instead of rewriting entire files.
- **Planning & Architecture Tasks** automatically go to **NVIDIA's Nemotron 3 Ultra**. 

## ✨ Features
* **Global `ai` Command:** Launch the interactive chat from any folder on your PC.
* **Auto-Routing:** Automatically picks the right AI brain based on your prompt's keywords.
* **File Reading (`/file`):** Reads `.pdf`, `.docx`, Excel, PowerPoint, and any code/text file.
* **Architecture Diagrams (`/diagram`):** Forces Nemotron to generate Mermaid.js charts for your systems.
* **Agent Skills (Safeguarded):** The AI can write files and run terminal commands to test code (always prompts you for `[Y/n]` permission first).

---

## 🚀 1-Minute Installation (Windows)

1. **Clone this repository** (or download and extract the ZIP):
   ```powershell
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

2. **Run the installer script:**
   ```powershell
   .\install.ps1
   ```

The script will automatically install dependencies, set up your OpenRouter API key, and create a global `ai` command on your system.

---

## 💻 How to Use

Once installed, just open **any** terminal (PowerShell, Command Prompt, or VS Code) and type:

```powershell
ai
```

### Interactive Commands:
* `/cd C:\my\folder` - Change your working directory.
* `/ls` - List files in the current folder.
* `/file app.py fix the bug` - Reads the file and sends it to the AI.
* `/diagram how does a web server work` - Generates a Mermaid.js diagram.
* `/laguna [prompt]` - Force the Coder model.
* `/nemotron [prompt]` - Force the Architect model.

### Quick One-Shot Question:
Don't want to open the chat? Just ask your question directly:
```powershell
ai "Write a python script to scrape a website"
```
