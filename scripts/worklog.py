#!/usr/bin/env python3
"""Project-local, append-only SDLC work log and offline HTML exporter (stdlib only)."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SECTIONS = ("context", "questions", "hld", "lld", "decisions", "progress")
STATUSES = ("proposed", "discussed", "approved", "rejected", "superseded", "observed")
HEADINGS = {
    "context": "Prompts and understanding",
    "questions": "Questions asked and answers",
    "hld": "High-level design",
    "lld": "Low-level design",
    "decisions": "Decisions and revisions",
    "progress": "Chronological work log",
}

@contextmanager
def locked(folder: Path):
    """Use an OS file lock to serialize writers and projections."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".lock").open("a+b") as f:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            f.write(b"0")
            f.flush()
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(value)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def read_events(folder: Path) -> list[dict]:
    entries = []
    for file in (folder / "events").glob("*.json"):
        with file.open(encoding="utf-8") as f:
            event = json.load(f)
        if event.get("section") not in SECTIONS:
            raise ValueError(f"invalid section in {file}")
        entries.append(event)
    return sorted(entries, key=lambda x: (x["timestamp"], x["id"]))

def markdown_entries(events: list[dict], section: str) -> str:
    title = HEADINGS[section]
    selected = events if section == "progress" else [e for e in events if e["section"] == section]
    lines = [f"# {title}", "", "Generated from immutable .worklog/events records; edit using the worklog CLI.", ""]
    for e in selected:
        lines += [
            f"## {e['title']}", "",
            f"- Event: `{e['id']}`",
            f"- Time: {e['timestamp']}",
            f"- Section: {e['section']}",
            f"- Status: {e['status']}",
        ]
        if e.get("supersedes"):
            lines.append(f"- Supersedes: `{e['supersedes']}`")
        if e.get("source"):
            lines.append(f"- Source: {e['source']}")
        lines += ["", e["body"], ""]
    return "\n".join(lines) + "\n"

def projections(folder: Path, events: list[dict]) -> None:
    for section in SECTIONS:
        filename = "work-log.md" if section == "progress" else section + ".md"
        atomic_text(folder / filename, markdown_entries(events, section))
    # The overall chronology includes all events, not only progress events.
    atomic_text(folder / "work-log.md", markdown_entries(events, "progress"))

def simple_mermaid_svg(source: str) -> str | None:
    """Render basic Mermaid flowcharts offline. Keep source visible for unsupported syntax."""
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not lines or not re.fullmatch(r"(?:flowchart|graph)\s+(?:TD|TB|LR)", lines[0]):
        return None
    node_pat = r"([A-Za-z][\w-]*)(?:\[([^\]\n]+)\])?"
    edge_pat = re.compile("^" + node_pat + r"\s*-->\s*" + node_pat + "$")
    nodes = {}
    edges = []
    for line in lines[1:]:
        m = edge_pat.fullmatch(line)
        if m is None:
            return None
        start, start_name, end, end_name = m.groups()
        nodes.setdefault(start, start_name or start)
        nodes.setdefault(end, end_name or end)
        if start_name:
            nodes[start] = start_name
        if end_name:
            nodes[end] = end_name
        edges.append((start, end))
    if not nodes or len(nodes) > 24:
        return None
    positions = {key: 20 + i * 88 for i, key in enumerate(nodes)}
    height = len(nodes) * 88 + 30
    parts = ['<svg role="img" aria-label="Project flowchart" viewBox="0 0 560 ' +
             str(height) + '" xmlns="http://www.w3.org/2000/svg">']
    for start, end in edges:
        parts.append('<path d="M 280 ' + str(positions[start] + 62) +
                     ' L 280 ' + str(positions[end] - 4) +
                     '" stroke="#475569" stroke-width="2" fill="none"/>')
    for key, label in nodes.items():
        y = positions[key]
        parts.append('<rect x="28" y="' + str(y) +
                     '" width="504" height="60" rx="10" fill="#e2e8f0" stroke="#64748b"/>')
        parts.append('<text x="280" y="' + str(y + 35) +
                     '" text-anchor="middle" font-family="system-ui" font-size="15" fill="#0f172a">' +
                     html.escape(label[:85]) + '</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def body_html(text: str) -> str:
    """Conservative Markdown subset. Never interpret user HTML or JavaScript."""
    output, paragraph = [], []
    lines = text.splitlines()
    code, fence, lang = [], False, ""
    def flush() -> None:
        if paragraph:
            output.append("<p>" + html.escape("\n".join(paragraph)) + "</p>")
            paragraph.clear()
    for line in lines:
        if line.strip().startswith("```"):
            flush()
            if fence:
                content = html.escape("\n".join(code))
                output.append('<pre><code class="language-' + html.escape(lang, quote=True) + '">' + content + "</code></pre>")
                if lang == "mermaid":
                    diagram = simple_mermaid_svg("\n".join(code))
                    if diagram:
                        output.append('<figure class="diagram">' + diagram + '<figcaption>Offline flowchart (simple Mermaid subset)</figcaption></figure>')
                code, fence = [], False
            else:
                lang = re.sub(r"[^a-zA-Z0-9_-]", "", line.strip()[3:].strip())[:32]
                fence = True
            continue
        if fence:
            code.append(line)
        elif not line.strip():
            flush()
        elif line.startswith("### "):
            flush()
            output.append("<h4>" + html.escape(line[4:]) + "</h4>")
        elif line.startswith("## "):
            flush()
            output.append("<h3>" + html.escape(line[3:]) + "</h3>")
        elif line.startswith("# "):
            flush()
            output.append("<h2>" + html.escape(line[2:]) + "</h2>")
        elif line.startswith("- "):
            flush()
            output.append("<p>• " + html.escape(line[2:]) + "</p>")
        else:
            paragraph.append(line)
    if fence:
        output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    flush()
    return "\n".join(output)

def render(folder: Path, events: list[dict]) -> Path:
    navigation = " ".join(
        '<a href="#' + section + '">' + HEADINGS[section] + "</a>" for section in SECTIONS
    )
    blocks = []
    for section in SECTIONS:
        relevant = events if section == "progress" else [e for e in events if e["section"] == section]
        cards = []
        for e in relevant:
            label = html.escape(e["status"])
            metadata = html.escape(e["timestamp"] + " · " + e["id"])
            if e.get("supersedes"):
                metadata += " · supersedes " + html.escape(e["supersedes"])
            cards.append(
                '<article><h3>' + html.escape(e["title"]) + '</h3><p class="meta">' +
                label + ' · ' + metadata + '</p>' + body_html(e["body"]) + '</article>'
            )
        blocks.append('<section id="' + section + '"><h2>' + HEADINGS[section] + '</h2>' +
                      ("\n".join(cards) if cards else "<p>No entries yet.</p>") + "</section>")
    # This SVG is a built-in overview; fenced Mermaid remains readable offline as source.
    diagram = """<svg role="img" aria-label="Project work log data flow: Skills to event records to HTML" viewBox="0 0 720 88" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="12" width="176" height="60" rx="10" fill="#243b53"/>
      <rect x="272" y="12" width="176" height="60" rx="10" fill="#243b53"/>
      <rect x="536" y="12" width="176" height="60" rx="10" fill="#243b53"/>
      <g font-family="system-ui" font-size="16" text-anchor="middle" fill="white">
        <text x="96" y="48">Agent skills</text><text x="360" y="48">Event records</text><text x="624" y="48">HTML dashboard</text>
      </g><g stroke="#64748b" stroke-width="3" fill="none"><path d="M184 42H260m-8 -7 8 7 -8 7M448 42H524m-8 -7 8 7 -8 7"/></g>
    </svg>"""
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Work Log</title><style>
:root{color-scheme:light}body{font:16px/1.6 system-ui,sans-serif;background:#f7f9fc;color:#162334;margin:0}
header,main{max-width:1050px;margin:auto;padding:22px}header{padding-top:32px}
nav{display:flex;flex-wrap:wrap;gap:12px}a{color:#164b8c}a:focus-visible{outline:3px solid #d97706;outline-offset:3px}
section{margin:36px 0}article{background:#fff;border:1px solid #c7d1dc;border-radius:12px;padding:20px;margin:14px 0}
.meta{color:#44546a;font-size:.9rem;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-x:auto;background:#172433;color:#f5f7fb;padding:16px;border-radius:8px}
code{font-family:ui-monospace,SFMono-Regular,monospace}p{white-space:pre-wrap;overflow-wrap:anywhere}
svg{max-width:100%;height:auto}h1,h2,h3{line-height:1.3}
</style></head><body><header><h1>Project Work Log</h1>
<p>Offline, generated view of recorded prompts, questions, designs and decisions. Statuses reflect explicit records, not inferred approval.</p>
<nav>""" + navigation + """</nav></header><main>""" + diagram + "\n".join(blocks) + """</main></body></html>"""
    path = folder / "index.html"
    atomic_text(path, page)
    return path.resolve()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Target project root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create a per-project .worklog")
    add = sub.add_parser("record", help="Add an immutable event and refresh Markdown")
    add.add_argument("--section", choices=SECTIONS, required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--body", help="Event content; prefer --body-file for multiline text")
    add.add_argument("--body-file", type=Path)
    add.add_argument("--status", choices=STATUSES, default="discussed")
    add.add_argument("--source", default="")
    add.add_argument("--supersedes", default="")
    sub.add_parser("render", help="Regenerate Markdown and offline HTML")
    args = parser.parse_args()
    folder = Path(args.project).expanduser().resolve() / ".worklog"
    try:
        if args.command == "record":
            if (args.body is None) == (args.body_file is None):
                parser.error("specify exactly one of --body or --body-file")
            body = args.body if args.body is not None else args.body_file.read_text(encoding="utf-8")
            if not body.strip() or not args.title.strip():
                parser.error("title and body must not be empty")
        with locked(folder):
            events = read_events(folder)
            if args.command == "record":
                if args.supersedes and args.supersedes not in {e["id"] for e in events}:
                    parser.error("--supersedes must refer to an existing event ID")
                event = {
                    "schema_version": 1, "id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "section": args.section, "title": args.title,
                    "body": body, "status": args.status,
                    "source": args.source, "supersedes": args.supersedes
                }
                event_path = folder / "events" / (event["id"] + ".json")
                event_path.parent.mkdir(parents=True, exist_ok=True)
                with event_path.open("x", encoding="utf-8") as out:
                    json.dump(event, out, ensure_ascii=False, indent=2)
                    out.write("\n")
                events.append(event)
                events.sort(key=lambda e: (e["timestamp"], e["id"]))
                print("Recorded:", event["id"])
            projections(folder, events)
            if args.command == "render":
                print("HTML:", render(folder, events))
            else:
                print("Work log:", folder.resolve())
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("worklog error:", exc, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
