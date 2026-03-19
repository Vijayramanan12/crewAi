"""
Frontend Digest Viewer
──────────────────────
Flask server that serves the knowledge/ markdown reports
as a browsable, searchable web interface.

Run:  python viewer/app.py
Open: http://localhost:5000
"""

import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, render_template, abort, request

# ── Dynamic Path Fix (allow importing from src/) ──────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from tools import analyze_url
from analz_frontend.live_crew import LiveAnalystCrew

app = Flask(__name__)

# ── Path to knowledge folder (relative to project root) ──────
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


def parse_date(filename: str):
    """Extract date from filename like frontend_digest_2026-03-16.md"""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return datetime.min

def parse_category(filename: str) -> str:
    """Extract category from frontend_digest_{category}_{date}.md"""
    # Matches letters/hyphens between 'frontend_digest_' and the date part
    match = re.search(r"frontend_digest_([a-zA-Z-]+)_", filename)
    if match:
        return match.group(1).replace("-", " ")
    return "General"



def get_all_reports():
    """Return sorted list of report metadata from knowledge/ folder."""
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    files = sorted(
        KNOWLEDGE_DIR.glob("frontend_digest_*.md"),
        key=lambda f: parse_date(f.name),
        reverse=True,
    )
    reports = []
    for f in files:
        date_obj = parse_date(f.name)
        reports.append({
            "filename": f.name,
            "slug": f.stem,
            "date": date_obj.strftime("%B %d, %Y") if date_obj != datetime.min else f.stem,
            "date_short": date_obj.strftime("%Y-%m-%d") if date_obj != datetime.min else "",
            "day": date_obj.strftime("%A") if date_obj != datetime.min else "",
            "category": parse_category(f.name),
            "size_kb": round(f.stat().st_size / 1024, 1),
        })
    return reports


def extract_preview(content: str, max_chars=200) -> str:
    """Get a plain-text preview from markdown content."""
    # Strip markdown syntax for preview
    text = re.sub(r"#+\s*", "", content)
    text = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r">\s*", "", text)
    text = re.sub(r"\n+", " ", text).strip()
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


def extract_sites(content: str) -> list:
    """Extract site names from report headings. Handles formats like '## 1.', '## [1]', '## **[1]**' etc."""
    # Matches headings starting with 1-3 hashes, followed by some numbering pattern, and capturing the text after
    matches = re.findall(r"^#{1,3}\s+(?:[*_\[(]*\d+[*_\]\)\.\s]*)+\s*(.+)$", content, re.MULTILINE)
    # Clean up any trailing markdown bolding/italics
    return [m.strip(" *-_") for m in matches if m.strip()]


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/reports")
def api_reports():
    reports = get_all_reports()
    # Enrich with preview
    for r in reports:
        path = KNOWLEDGE_DIR / r["filename"]
        try:
            content = path.read_text(encoding="utf-8")
            r["preview"] = extract_preview(content)
            r["sites"] = extract_sites(content)
            r["site_count"] = len(r["sites"])
        except Exception:
            r["preview"] = ""
            r["sites"] = []
            r["site_count"] = 0
    return jsonify(reports)


@app.route("/api/report/<slug>")
def api_report(slug):
    path = KNOWLEDGE_DIR / f"{slug}.md"
    if not path.exists():
        abort(404)
    content = path.read_text(encoding="utf-8")
    date_obj = parse_date(slug)
    return jsonify({
        "slug": slug,
        "filename": path.name,
        "date": date_obj.strftime("%B %d, %Y") if date_obj != datetime.min else slug,
        "day": date_obj.strftime("%A") if date_obj != datetime.min else "",
        "content": content,
        "sites": extract_sites(content),
    })


@app.route("/api/search")
def api_search():
    from flask import request
    query = request.args.get("q", "").lower().strip()
    if not query:
        return jsonify([])

    results = []
    for f in KNOWLEDGE_DIR.glob("frontend_digest_*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            if query in content.lower():
                date_obj = parse_date(f.name)
                # Find matching lines for context
                matches = []
                for line in content.splitlines():
                    if query in line.lower():
                        matches.append(line.strip())
                        if len(matches) >= 3:
                            break
                results.append({
                    "slug": f.stem,
                    "filename": f.name,
                    "date": date_obj.strftime("%B %d, %Y") if date_obj != datetime.min else f.stem,
                    "matches": matches,
                })
        except Exception:
            continue
    return jsonify(results)


@app.route("/api/stats")
def api_stats():
    reports = get_all_reports()
    all_content = ""
    all_sites = []
    all_libs = []

    lib_patterns = [
        "GSAP", "Three.js", "Framer Motion", "Lenis", "Tailwind",
        "Next.js", "Nuxt", "Astro", "SvelteKit", "Barba.js",
        "CSS @layer", "Container Queries", "View Transitions", "WebGL",
    ]

    for r in reports:
        path = KNOWLEDGE_DIR / r["filename"]
        try:
            content = path.read_text(encoding="utf-8")
            all_content += content
            all_sites.extend(extract_sites(content))
            for lib in lib_patterns:
                if lib.lower() in content.lower():
                    all_libs.append(lib)
        except Exception:
            continue

    lib_freq = {}
    for lib in all_libs:
        lib_freq[lib] = lib_freq.get(lib, 0) + 1

    top_libs = sorted(lib_freq.items(), key=lambda x: x[1], reverse=True)[:8]

    return jsonify({
        "total_reports": len(reports),
        "total_sites": len(all_sites),
        "top_libraries": [{"name": k, "count": v} for k, v in top_libs],
        "latest": reports[0]["date"] if reports else None,
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Chat with a specific report (or all reports) using the OpenAI API.
    Body: { "message": str, "slug": str|null, "history": [...] }
    """
    import openai

    body = request.get_json(force=True)
    user_message = body.get("message", "").strip()
    slug = body.get("slug")  # None = chat across all reports
    history = body.get("history", [])  # prior turns [{"role":..,"content":..}]

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # ── Build context from report(s) ──────────────────────

    context_md = ""
    if slug:
        path = KNOWLEDGE_DIR / f"{slug}.md"
        if path.exists():
            context_md = path.read_text(encoding="utf-8")
            label = f"the report: {slug}"
        else:
            return jsonify({"error": "Report not found"}), 404
    else:
        # Load all reports, newest first, cap at ~40k chars
        files = sorted(
            KNOWLEDGE_DIR.glob("frontend_digest_*.md"),
            key=lambda f: parse_date(f.name),
            reverse=True,
        )
        parts = []
        total = 0
        for f in files:
            txt = f.read_text(encoding="utf-8")
            if total + len(txt) > 40000:
                break
            parts.append(f"--- {f.stem} ---\n{txt}")
            total += len(txt)
        context_md = "\n\n".join(parts)
        label = "all available reports"

    system_prompt = f"""You are a knowledgeable frontend development assistant embedded inside the Frontend Digest viewer — a tool that analyzes cutting-edge websites for unique CSS, JavaScript, and design patterns.

You have been given the full content of {label} as your knowledge base. Answer questions about the techniques, libraries, code snippets, sites, and trends documented in these reports. Be specific and technical — your audience are frontend developers.

When referencing a technique from the report, quote or paraphrase directly from the relevant section. If asked about something not covered in the reports, say so clearly and offer related context if available.

Keep responses concise but precise. Use markdown formatting for code snippets.

--- REPORT CONTENT START ---
{context_md}
--- REPORT CONTENT END ---"""

    # ── Build message history ─────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history[-10:]:  # keep last 10 turns for context window
        if turn.get("role") in ("user", "assistant"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    # ── Call OpenAI API ────────────────────────────────
    try:
        client = openai.OpenAI(
        api_key="sk-no-key-needed",
        base_url="http://127.0.0.1:1234/v1"
        )
        response = client.chat.completions.create(
        model="ministral-3-3b",
        messages=messages,
        max_tokens=3000,
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyze")
def api_analyze():
    url = request.args.get("url", "").strip()
    if not url or not url.startswith("http"):
        return jsonify({"error": "Valid URL required"}), 400
    
    try:
        results = analyze_url(url)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/research", methods=["POST"])
def api_research():
    """Run full AI Research Crew on a URL."""
    body = request.get_json(force=True)
    url = body.get("url", "").strip()
    if not url or not url.startswith("http"):
        return jsonify({"error": "Valid URL required"}), 400
    
    try:
        # Initialize the AI Analyst Crew
        crew_instance = LiveAnalystCrew().crew()
        # Trigger the analysis
        result = crew_instance.kickoff(inputs={"url": url})
        
        # Save this to a pseudo-report if desired, but for now just return it
        # return the raw output as markdown
        return jsonify({
            "report": result.raw if hasattr(result, 'raw') else str(result),
            "url": url,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n🌐  Frontend Digest Viewer")
    print(f"    Knowledge dir: {KNOWLEDGE_DIR}")
    print("    Open: http://localhost:5001\n")
    app.run(debug=True, port=5001)