"""
Dual-Model Router — Automatically sends your prompt to the right model.

Usage:
    python router.py "Write a function that sorts a list"       -> Laguna
    python router.py "Design the architecture for a chat app"   -> Nemotron
    python router.py                                            -> Interactive mode
    
In interactive mode:
    /laguna <prompt>    Force Laguna S 2.1
    /nemotron <prompt>  Force Nemotron 3 Ultra
    quit                Exit
"""

import os
import sys
import re
import subprocess

# Fix Windows console encoding — models return emojis, math symbols, etc.
# that cp1252 can't handle. Force UTF-8 on both stdout and stderr.
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

LAGUNA = "poolside/laguna-s-2.1:free"
NEMOTRON = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Working directory for /file, /ls. Defaults to where you launched the script.
WORKDIR = os.getcwd()

# Keywords that signal a CODING task -> Laguna
CODE_SIGNALS = [
    "write", "implement", "code", "function", "class", "fix", "bug",
    "debug", "test", "refactor", "optimize", "convert", "parse",
    "generate", "script", "snippet", "syntax", "error", "exception",
    "api endpoint", "crud", "query", "sql", "html", "css", "dockerfile",
    "unit test", "pytest", "import", "install", "pip", "npm",
    "regex", "algorithm", "data structure", "sort", "search",
]

# Keywords that signal a REASONING task -> Nemotron
REASON_SIGNALS = [
    "design", "architect", "plan", "strategy", "compare", "tradeoff",
    "trade-off", "should i", "pros and cons", "recommend", "explain",
    "why", "analyze", "review architecture", "brainstorm", "evaluate",
    "decision", "approach", "methodology", "best practice", "pattern",
    "migrate", "scale", "deploy", "roadmap", "risk", "security",
    "threat model", "post-mortem", "root cause", "incident",
    "requirements", "specification", "proposal", "research",
]


def pick_model(prompt: str) -> str:
    """Pick the best model based on prompt content."""
    lower = prompt.lower()
    code_score = sum(1 for kw in CODE_SIGNALS if kw in lower)
    reason_score = sum(1 for kw in REASON_SIGNALS if kw in lower)

    if code_score > reason_score:
        return LAGUNA
    elif reason_score > code_score:
        return NEMOTRON
    else:
        # Default: if it looks like it wants output code, use Laguna
        if any(marker in lower for marker in ["```", "def ", "class ", "return "]):
            return LAGUNA
        return NEMOTRON  # When in doubt, think first


def ask(prompt: str, model: str = None, is_diagram: bool = False) -> str:
    """Send a prompt to the appropriate model and return the response."""
    if model is None:
        model = pick_model(prompt)

    if is_diagram:
        model = NEMOTRON
        model_name = "Nemotron 3 Ultra (Diagram Architect)"
    else:
        model_name = "Laguna S 2.1 (Senior Dev)" if "laguna" in model else "Nemotron 3 Ultra (Architect)"

    print(f"\n{'='*60}")
    print(f"  Routing to: {model_name}")
    print(f"  Model ID:   {model}")
    print(f"{'='*60}\n")

    # Dynamic system message based on model
    if "laguna" in model:
        system_msg = (
            "You are a Senior Developer answering in a terminal. Keep responses concise. "
            "Follow the 'Ponytail' principle: Write less code when you don't need it. "
            "Do NOT rewrite entire files. Output only the necessary diffs or snippets needed to solve the problem. "
            "TOOLS: You can write files or run commands to help the user. "
            "To edit/write a file, output exactly:\n"
            "<WRITE_FILE path=\"filename.ext\">\ncontent here\n</WRITE_FILE>\n"
            "To run a command, output exactly:\n"
            "<RUN_CMD>\ncommand here\n</RUN_CMD>\n"
        )
    else:
        system_msg = (
            "You are a Master Architect answering in a terminal. Keep responses concise and readable. "
            "Use plain text and short bullet points. Avoid markdown tables unless necessary. "
            "TOOLS: You can write files or run commands to help the user. "
            "To edit/write a file, output exactly:\n"
            "<WRITE_FILE path=\"filename.ext\">\ncontent here\n</WRITE_FILE>\n"
            "To run a command, output exactly:\n"
            "<RUN_CMD>\ncommand here\n</RUN_CMD>\n"
        )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]

    import time
    max_loops = 3
    current_loop = 0
    final_content = ""

    while current_loop < max_loops:
        # Send request with retry logic
        max_retries = 3
        response = None
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                )
                break
            except Exception as e:
                if "429" in str(e) and attempt < max_retries:
                    wait = 5 * (attempt + 1)
                    print(f"  Rate limited. Retrying in {wait}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait)
                else:
                    print(f"  ERROR: {e}")
                    return None

        if response is None:
            break

        content = response.choices[0].message.content
        usage = response.usage
        print(content)
        final_content = content
        messages.append({"role": "assistant", "content": content})

        # Process tools
        tool_used = False
        
        # Check WRITE_FILE
        for match in re.finditer(r'<WRITE_FILE\s+path="([^"]+)">\n?(.*?)\n?</WRITE_FILE>', content, re.DOTALL):
            tool_used = True
            filepath = match.group(1).strip()
            filecontent = match.group(2)
            
            if not os.path.isabs(filepath):
                filepath = os.path.join(WORKDIR, filepath)
                
            print(f"\n[!] AI wants to WRITE to file: {filepath}")
            ans = input("    Allow this action? [Y/n]: ").strip().lower()
            if ans == 'y' or ans == '':
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(filecontent)
                    print(f"    Success: Wrote to {filepath}")
                    messages.append({"role": "user", "content": f"Tool output: Successfully wrote to {filepath}."})
                except Exception as e:
                    print(f"    Error: {e}")
                    messages.append({"role": "user", "content": f"Tool output: Error writing file: {e}"})
            else:
                print("    Action denied by user.")
                messages.append({"role": "user", "content": "Tool output: Action denied by user. Do not try this again."})

        # Check RUN_CMD
        for match in re.finditer(r'<RUN_CMD>\n?(.*?)\n?</RUN_CMD>', content, re.DOTALL):
            tool_used = True
            cmd = match.group(1).strip()
            
            print(f"\n[!] AI wants to RUN COMMAND: {cmd}")
            ans = input("    Allow this action? [Y/n]: ").strip().lower()
            if ans == 'y' or ans == '':
                try:
                    print(f"    Running: {cmd} ...")
                    result = subprocess.run(cmd, shell=True, cwd=WORKDIR, capture_output=True, text=True)
                    out = (result.stdout + result.stderr).strip()
                    if not out:
                        out = "Command executed successfully with no output."
                    print("    Done.")
                    # Cap output length
                    if len(out) > 2000:
                        out = out[:2000] + "\n...[Output Truncated]..."
                    messages.append({"role": "user", "content": f"Tool output from '{cmd}':\n{out}"})
                except Exception as e:
                    print(f"    Error: {e}")
                    messages.append({"role": "user", "content": f"Tool output: Error running command: {e}"})
            else:
                print("    Action denied by user.")
                messages.append({"role": "user", "content": "Tool output: Action denied by user. Do not try this again."})

        if not tool_used:
            print(f"\n{'-'*60}")
            print(f"Tokens -- in: {usage.prompt_tokens}, out: {usage.completion_tokens}, total: {usage.total_tokens}")
            break
            
        current_loop += 1
        if current_loop < max_loops:
            print("\n  [AI is thinking about the result...]\n")
        else:
            print("\n  [Auto-loop limit reached (3). Stopping.]")
            print(f"\n{'-'*60}")
            print(f"Tokens -- in: {usage.prompt_tokens}, out: {usage.completion_tokens}, total: {usage.total_tokens}")

    return final_content


def read_file(path: str) -> str:
    """Read a file of any supported type and return its text contents."""
    path = path.strip().strip('"').strip("'")

    # Resolve relative paths against WORKDIR
    if not os.path.isabs(path):
        path = os.path.join(WORKDIR, path)

    if not os.path.isfile(path):
        print(f"  ERROR: File not found: {path}")
        return None

    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".pdf":
            content = _read_pdf(path)
        elif ext == ".docx":
            content = _read_docx(path)
        elif ext in (".xlsx", ".xls"):
            content = _read_excel(path)
        elif ext == ".pptx":
            content = _read_pptx(path)
        else:
            # Plain text fallback (.py, .js, .txt, .json, .csv, .md, .yaml, etc.)
            content = _read_text(path)

        if content is None:
            return None

        size = len(content)
        print(f"  Read: {path}")
        print(f"  Type: {ext if ext else 'text'}")
        print(f"  Size: {size:,} chars extracted")
        if size > 50000:
            print(f"  WARNING: File is large ({size:,} chars). This will use many tokens.")
        if size == 0:
            print(f"  WARNING: No text content extracted from file.")
            return None
        return content

    except Exception as e:
        print(f"  ERROR reading file: {e}")
        return None


def _read_text(path: str) -> str:
    """Read a plain text file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_pdf(path: str) -> str:
    """Extract text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        print("  ERROR: PyPDF2 not installed. Run: pip install PyPDF2")
        return None

    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            pages.append(f"--- Page {i} ---\n{text.strip()}")

    if not pages:
        print("  WARNING: PDF has no extractable text (might be scanned/image-based).")
        return None
    return "\n\n".join(pages)


def _read_docx(path: str) -> str:
    """Extract text from a Word .docx file."""
    try:
        from docx import Document
    except ImportError:
        print("  ERROR: python-docx not installed. Run: pip install python-docx")
        return None

    doc = Document(path)
    parts = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)

    # Also read tables
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            parts.append(" | ".join(cells))

    return "\n".join(parts)


def _read_excel(path: str) -> str:
    """Extract text from an Excel .xlsx/.xls file."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        print("  ERROR: openpyxl not installed. Run: pip install openpyxl")
        return None

    wb = load_workbook(path, read_only=True, data_only=True)
    parts = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"--- Sheet: {sheet_name} ---")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            # Skip completely empty rows
            if any(cells):
                parts.append(" | ".join(cells))

    wb.close()
    return "\n".join(parts)


def _read_pptx(path: str) -> str:
    """Extract text from a PowerPoint .pptx file."""
    try:
        from pptx import Presentation
    except ImportError:
        print("  ERROR: python-pptx not installed. Run: pip install python-pptx")
        return None

    prs = Presentation(path)
    parts = []

    for i, slide in enumerate(prs.slides, 1):
        slide_texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        slide_texts.append(text)
            # Also read tables in slides
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    slide_texts.append(" | ".join(cells))
        if slide_texts:
            parts.append(f"--- Slide {i} ---\n" + "\n".join(slide_texts))

    return "\n\n".join(parts)


def parse_file_command(user_input: str):
    """Parse /file <path> <instruction> and return (file_content, instruction, model).
    
    Supports:
        /file C:\\path\\to\\file.py fix the bug
        /file "C:\\path with spaces\\file.py" fix the bug
        /file C:\\path\\file.py                          (no instruction = "Review this file")
    """
    rest = user_input[6:].strip()  # Remove "/file "
    
    # Handle quoted path
    if rest.startswith('"'):
        end_quote = rest.find('"', 1)
        if end_quote == -1:
            return None, None
        path = rest[1:end_quote]
        instruction = rest[end_quote + 1:].strip()
    elif rest.startswith("'"):
        end_quote = rest.find("'", 1)
        if end_quote == -1:
            return None, None
        path = rest[1:end_quote]
        instruction = rest[end_quote + 1:].strip()
    else:
        # Unquoted: first token is path, rest is instruction
        parts = rest.split(None, 1)
        if not parts:
            return None, None
        path = parts[0]
        instruction = parts[1] if len(parts) > 1 else ""
    
    if not instruction:
        instruction = "Review this file and explain what it does"
    
    return path, instruction


def show_help():
    """Print available commands."""
    print()
    print("  Commands:")
    print("  ─────────────────────────────────────────────────")
    print("  (just type)        Ask a question (auto-picks model)")
    print("  /laguna <prompt>   Force Laguna S 2.1 (coding)")
    print("  /nemotron <prompt> Force Nemotron 3 Ultra (reasoning)")
    print("  /diagram <prompt>  Force Nemotron to draw a Mermaid.js diagram")
    print("  /file <path> <instruction>")
    print("                     Read a file and send it with your instruction")
    print("  /cd <path>         Change the current working directory")
    print("  /ls                List files in the current working directory")
    print("  /help              Show this help")
    print("  quit               Exit")
    print()
    print("  Supported file types:")
    print("    .txt .py .js .json .csv .md .yaml .html .css  (any text file)")
    print("    .pdf  .docx  .xlsx/.xls  .pptx")
    print()
    print("  Examples:")
    print("    /cd C:\\Users\\wasif\\Documents\\wheels")
    print("    /ls")
    print("    /diagram Explain the flow of a chat app")
    print("    /file app.py fix the bug in this  (uses relative path!)")
    print()


def interactive():
    """Run an interactive loop."""
    global WORKDIR
    print()
    print("+" + "=" * 66 + "+")
    print("|  Dual-Model Router: Laguna S 2.1 + Nemotron 3 Ultra            |")
    print("|  Commands: /laguna /nemotron /diagram /file /cd /ls /help quit |")
    print("+" + "=" * 66 + "+")

    while True:
        try:
            prompt = input(f"\n[{WORKDIR}]\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not prompt:
            continue

        if prompt.lower() == "quit":
            print("Goodbye!")
            break

        if prompt.lower() == "/help":
            show_help()
            continue

        if prompt.lower().startswith("/cd "):
            new_dir = prompt[4:].strip().strip('"').strip("'")
            if not os.path.isabs(new_dir):
                new_dir = os.path.join(WORKDIR, new_dir)
            new_dir = os.path.abspath(new_dir)
            if os.path.isdir(new_dir):
                WORKDIR = new_dir
            else:
                print(f"  ERROR: Directory not found: {new_dir}")
            continue

        if prompt.lower() == "/ls":
            try:
                items = os.listdir(WORKDIR)
                print(f"  Contents of {WORKDIR}:")
                for item in sorted(items):
                    item_path = os.path.join(WORKDIR, item)
                    if os.path.isdir(item_path):
                        print(f"    [DIR]  {item}")
                    else:
                        print(f"    [FILE] {item}")
            except Exception as e:
                print(f"  ERROR listing directory: {e}")
            continue

        # /file command: read a file and include its contents in the prompt
        if prompt.lower().startswith("/file "):
            path, instruction = parse_file_command(prompt)
            if path is None:
                print("  Usage: /file <path> <instruction>")
                print("  Example: /file app.py fix the bug")
                continue
            
            content = read_file(path)
            if content is None:
                continue

            # Get just the filename for a cleaner prompt
            filename = os.path.basename(path)
            prompt = f"{instruction}\n\nFile: {filename}\n\n{content}"
            ask(prompt)
            continue

        # Handle /diagram
        if prompt.lower().startswith("/diagram "):
            subject = prompt[9:].strip()
            diagram_prompt = f"Create a comprehensive Mermaid.js architecture diagram for the following. Output ONLY the raw mermaid code inside a ```mermaid block. Do not use any tools.\n\n{subject}"
            ask(diagram_prompt, is_diagram=True)
            continue

        # Allow forcing a specific model
        forced_model = None
        if prompt.lower().startswith("/laguna "):
            forced_model = LAGUNA
            prompt = prompt[8:]
        elif prompt.lower().startswith("/nemotron "):
            forced_model = NEMOTRON
            prompt = prompt[10:]

        ask(prompt, model=forced_model)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI mode: python router.py "your prompt here"
        ask(" ".join(sys.argv[1:]))
    else:
        # Interactive mode
        interactive()

