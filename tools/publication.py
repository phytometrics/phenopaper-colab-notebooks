#!/usr/bin/env python3
"""Publish validated Colab notebooks and render README from publication.json.

Only notebook JSON and its saved PNG outputs are read. Notebook code is never run.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import fcntl
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "publication.json"
README = REPO / "README.md"
SUMMARY = REPO / "assets" / "notebook-summary.svg"
SUMMARY_START = "<!-- publication-summary:start -->"
SUMMARY_END = "<!-- publication-summary:end -->"
START = "<!-- publication-table:start -->"
END = "<!-- publication-table:end -->"
PUBLIC_ID = re.compile(r"p-[a-f0-9]{32}\Z")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_PREVIEW_BYTES = 8_000_000


def fail(message: str) -> None:
    raise ValueError(message)


def clean_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{field} must be nonempty text")
    value = value.strip()
    if any(char in value for char in "\r\n|") or "<" in value or ">" in value:
        fail(f"{field} contains markup or table-breaking characters")
    return value


def validate_entry(entry: dict) -> None:
    public_id = entry.get("public_id")
    if not isinstance(public_id, str) or not PUBLIC_ID.fullmatch(public_id):
        fail(f"Invalid public_id: {public_id!r}")
    for field in ("title", "compute", "validated_on", "demonstration"):
        clean_text(entry.get(field), field)
    dt.date.fromisoformat(entry["validated_on"])
    if entry["compute"] not in {"CPU", "T4 GPU", "CPU + T4 GPU"}:
        fail(f"Unsupported compute label for {public_id}")
    doi = entry.get("doi")
    if doi is not None:
        clean_text(doi, "doi")
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            fail(f"Invalid DOI for {public_id}")
    tags = entry.get("semantic_tags")
    if not isinstance(tags, list) or not all(isinstance(t, str) and re.fullmatch(r"[a-z_]+:[a-z0-9_]+", t) for t in tags):
        fail(f"Invalid semantic tags for {public_id}")
    preview = entry.get("preview")
    if preview is not None:
        if not isinstance(preview, dict):
            fail(f"Invalid preview for {public_id}")
        clean_text(preview.get("alt"), "preview.alt")
        clean_text(preview.get("caption"), "preview.caption")
        path = REPO / "assets" / "previews" / f"{public_id}.png"
        if not path.is_file() or not path.read_bytes().startswith(PNG_MAGIC):
            fail(f"Missing or invalid preview: {path}")
    notebook = REPO / "notebooks" / f"{public_id}.ipynb"
    if not notebook.is_file():
        fail(f"Missing notebook: {notebook}")


def load_manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("notebooks"), list):
        fail("publication.json must have schema_version 1 and notebooks array")
    seen = set()
    for entry in data["notebooks"]:
        validate_entry(entry)
        if entry["public_id"] in seen:
            fail(f"Duplicate public_id: {entry['public_id']}")
        seen.add(entry["public_id"])
    return data


def row(entry: dict) -> str:
    public_id = entry["public_id"]
    colab = f"https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/{public_id}.ipynb"
    paper = f"https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{public_id}"
    title = html.escape(entry["title"]).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    details = f"**{title}**<br><br>"
    details += f"[![Open in PhenoPaper](https://img.shields.io/badge/Open_in-PhenoPaper-356859?style=flat-square)]({paper}) "
    if entry.get("doi"):
        details += f"[![DOI paper](https://img.shields.io/badge/DOI-paper-326CE5?style=flat-square)](https://doi.org/{quote(entry['doi'], safe='/')}) "
    details += f"[![Open in Colab](https://img.shields.io/badge/Open_in-Colab-F9AB00?style=flat-square&logo=googlecolab&logoColor=white)]({colab}) "
    compute = entry["compute"]
    badge = {"CPU": ("CPU", "lightgrey"), "T4 GPU": ("T4%20GPU", "blue"), "CPU + T4 GPU": ("CPU%20%2B%20T4%20GPU", "purple")}[compute]
    details += f"[![Compute: {compute}](https://img.shields.io/badge/compute-{badge[0]}-{badge[1]}?style=flat-square)]({colab}) "
    date_badge = entry["validated_on"].replace("-", "--")
    details += f"![Validated {entry['validated_on']}](https://img.shields.io/badge/validated-{date_badge}-6c757d?style=flat-square) "
    details += f"<br><sub><b>Demonstration:</b> {html.escape(entry['demonstration'])}</sub>"
    if entry["semantic_tags"]:
        details += f"<br><br><sub><b>Semantic tags:</b> {', '.join(entry['semantic_tags'])}</sub>"
    preview = entry.get("preview")
    if preview:
        alt = html.escape(preview["alt"], quote=True)
        caption = html.escape(preview["caption"])
        image = f'<a href="{colab}"><img src="assets/previews/{public_id}.png" width="400" alt="{alt}" /></a><br><sub>{caption}</sub>'
    else:
        image = "—"
    return f"| {details} | {image} |"


def render_summary(data: dict) -> str:
    count = len(data["notebooks"])
    label_x = 48 + max(136, len(str(count)) * 64 + 28)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="240" viewBox="0 0 960 240" role="img" aria-labelledby="title description">
  <title id="title">PhenoPaper × Google Colab</title>
  <desc id="description">{count} execution-verified notebooks</desc>
  <defs>
    <linearGradient id="forest" x2="1" y2="1">
      <stop stop-color="#123d32"/>
      <stop offset="1" stop-color="#09291f"/>
    </linearGradient>
  </defs>
  <rect width="960" height="240" rx="24" fill="url(#forest)"/>
  <circle cx="911" cy="237" r="173" fill="#205240" opacity=".3"/>
  <circle cx="965" cy="211" r="116" fill="none" stroke="#a5c6ad" stroke-opacity=".12"/>
  <g transform="translate(48 39)" fill="none" stroke="#b5d9a9" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
    <path d="M15 29V11M15 21C3 23 0 16 1 8c9-1 15 3 14 13ZM15 14C15 3 24-1 32 1c0 9-5 15-17 13Z"/>
  </g>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="96" y="66" fill="#f1f6ed" font-size="29" font-weight="600">PhenoPaper <tspan fill="#95b6a5">×</tspan> Google Colab</text>
    <text x="46" y="185" fill="#ffffff" font-size="104" font-weight="700" letter-spacing="-5">{count}</text>
    <rect x="{label_x}" y="120" width="36" height="4" rx="2" fill="#f9ab00"/>
    <text x="{label_x}" y="154" fill="#f1f6ed" font-size="21" font-weight="600" letter-spacing="2">EXECUTION-VERIFIED</text>
    <text x="{label_x}" y="185" fill="#b2cbbc" font-size="19" font-weight="500" letter-spacing="3">NOTEBOOKS</text>
  </g>
  <g transform="translate(832 44)" fill="none" stroke-width="8" stroke-linecap="round">
    <path d="M27 9a17 17 0 1 0 0 26" stroke="#f9ab00"/>
    <path d="M47 9a17 17 0 1 1 0 26" stroke="#ffcc64"/>
  </g>
</svg>
'''


def write_summary(data: dict) -> None:
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(render_summary(data), encoding="utf-8")


def render(data: dict) -> str:
    current = README.read_text(encoding="utf-8")
    if current.count(START) != 1 or current.count(END) != 1:
        fail("README must contain exactly one publication-table marker pair")
    if current.count(SUMMARY_START) != 1 or current.count(SUMMARY_END) != 1:
        fail("README must contain exactly one publication-summary marker pair")
    count = len(data["notebooks"])
    before_summary, summary_rest = current.split(SUMMARY_START, 1)
    _, after_summary = summary_rest.split(SUMMARY_END, 1)
    card = f'<a href="#notebooks"><img src="assets/notebook-summary.svg" width="960" alt="PhenoPaper × Google Colab — {count} execution-verified notebooks" /></a>'
    current = before_summary + SUMMARY_START + "\n" + card + "\n" + SUMMARY_END + after_summary
    table = "\n".join(["| Paper and run details | Preview |", "| --- | --- |", *(row(e) for e in data["notebooks"])])
    before, rest = current.split(START, 1)
    _, after = rest.split(END, 1)
    return before + START + "\n" + table + "\n" + END + after


def check_notebook(path: Path) -> dict:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        fail("Notebook is not valid nbformat 4 JSON")
    code_cells = [c for c in notebook["cells"] if c.get("cell_type") == "code"]
    if not code_cells:
        fail("Notebook has no code cells")
    output_count = 0
    image_count = 0
    for cell in code_cells:
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                fail("Notebook contains an error output")
            output_count += 1
            if "image/png" in output.get("data", {}):
                image_count += 1
    if not output_count:
        fail("Notebook has no saved outputs")
    return {"notebook": notebook, "image_count": image_count}


def notebook_sources(notebook: dict) -> list:
    return [c.get("source") for c in notebook["cells"] if c.get("cell_type") == "code"]


def get_preview(notebook: dict, index: int) -> bytes:
    images = []
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            data = output.get("data", {}).get("image/png")
            if data is not None:
                images.append(data)
    if index < 0 or index >= len(images):
        fail(f"Preview index {index} is outside saved PNG range (0..{len(images)-1})")
    payload = images[index]
    if isinstance(payload, list):
        payload = "".join(payload)
    # nbformat permits line-wrapped base64 data in a saved output.
    payload = "".join(payload.split())
    try:
        image = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        fail(f"Saved PNG output could not be decoded: {exc}")
    if not image.startswith(PNG_MAGIC) or len(image) > MAX_PREVIEW_BYTES:
        fail("Saved PNG is invalid or larger than 8 MB")
    return image


def git(*args: str) -> str:
    result = subprocess.run(["git", "-C", str(REPO), *args], text=True, capture_output=True)
    if result.returncode:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def ensure_github_access() -> None:
    expected = "https://github.com/phytometrics/phenopaper-colab-notebooks.git"
    if git("remote", "get-url", "origin") != expected:
        fail("origin does not point to the dedicated PhenoPaper notebook repository")
    status = subprocess.run(["gh", "auth", "status"], text=True, capture_output=True)
    if status.returncode:
        fail("GitHub CLI is not authenticated in this process environment")
    access = subprocess.run(
        ["gh", "api", "repos/phytometrics/phenopaper-colab-notebooks", "--jq", ".full_name"],
        text=True, capture_output=True,
    )
    if access.returncode or access.stdout.strip() != "phytometrics/phenopaper-colab-notebooks":
        fail("GitHub CLI credential cannot access the publication repository; check token lifetime and repository permissions")
    # This setting is local to the persistent checkout; the token stays in gh's store/environment.
    git("config", "--local", "credential.helper", "!gh auth git-credential")


def publish(args: argparse.Namespace) -> None:
    if not PUBLIC_ID.fullmatch(args.public_id):
        fail("public_id must be p- followed by 32 lowercase hex digits")
    run_dir = args.run_dir.resolve()
    notebook_path = run_dir / "deliverables" / f"{args.public_id}.ipynb"
    api_path = run_dir / "sources" / "paper_api.json"
    report_path = run_dir / "deliverables" / "report.md"
    if not all(p.is_file() for p in (notebook_path, api_path, report_path)):
        fail("Run must contain final notebook, paper_api.json, and report.md")
    api = json.loads(api_path.read_text(encoding="utf-8"))["data"]
    if api.get("public_id") != args.public_id:
        fail("PhenoPaper public_id does not match final notebook filename")
    result = check_notebook(notebook_path)
    executed = check_notebook(args.executed_output.resolve())
    if notebook_sources(result["notebook"]) != notebook_sources(executed["notebook"]):
        fail("Final notebook code differs from archived Colab output")
    final_outputs = [c.get("outputs", []) for c in result["notebook"]["cells"] if c.get("cell_type") == "code"]
    archived_outputs = [c.get("outputs", []) for c in executed["notebook"]["cells"] if c.get("cell_type") == "code"]
    if final_outputs != archived_outputs:
        fail("Final notebook outputs differ from archived Colab output")
    if not args.cli_log.is_file() or args.cli_log.stat().st_size < 100:
        fail("Archived Colab CLI log is missing or empty")
    # Colab CLI can leave execution_count null, but its session log records each cell.
    code_count = len(notebook_sources(result["notebook"]))
    execution_count = len(re.findall(r"^### Execution\b", args.cli_log.read_text(encoding="utf-8"), re.M))
    if execution_count < code_count:
        fail(f"CLI log has {execution_count} executions for {code_count} code cells")
    report = report_path.read_text(encoding="utf-8").lower()
    if any(term in report for term in ("code-only / not executed", "execution failed", "not validated")):
        fail("Report indicates notebook is unexecuted or failed")
    image = get_preview(result["notebook"], args.preview_index)
    entry = {
        "public_id": args.public_id,
        "title": api.get("title"),
        "doi": api.get("doi"),
        "compute": args.compute,
        "validated_on": args.validated_on,
        "demonstration": args.demonstration,
        "semantic_tags": api.get("tags") or [],
        "preview": {"alt": args.preview_caption, "caption": args.preview_caption},
    }
    # Text and identifiers are validated before any repository mutation.
    for field in ("title", "compute", "validated_on", "demonstration"):
        clean_text(entry[field], field)
    clean_text(args.preview_caption, "preview_caption")
    dt.date.fromisoformat(args.validated_on)
    if args.compute not in {"CPU", "T4 GPU", "CPU + T4 GPU"}:
        fail("Unsupported compute label")
    with (REPO / ".git" / "publication.lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        if git("status", "--porcelain"):
            fail("Publication repository has uncommitted changes")
        ensure_github_access()
        git("pull", "--ff-only", "origin", "main")
        data = load_manifest()
        existing = next((e for e in data["notebooks"] if e["public_id"] == args.public_id), None)
        target_notebook = REPO / "notebooks" / f"{args.public_id}.ipynb"
        target_preview = REPO / "assets" / "previews" / f"{args.public_id}.png"
        if existing and not args.replace:
            if target_notebook.read_bytes() == notebook_path.read_bytes():
                print(f"Already published: {args.public_id}")
                return
            fail("Notebook already exists; pass --replace for an intentional update")
        if existing:
            data["notebooks"].remove(existing)
        data["notebooks"].append(entry)
        shutil.copyfile(notebook_path, target_notebook)
        target_preview.write_bytes(image)
        MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        load_manifest()
        README.write_text(render(data), encoding="utf-8")
        write_summary(data)
        git("add", "--", str(target_notebook.relative_to(REPO)), str(target_preview.relative_to(REPO)), "publication.json", "README.md", str(SUMMARY.relative_to(REPO)))
        if not git("diff", "--cached", "--name-only"):
            print(f"Already up to date: {args.public_id}")
            return
        git("commit", "-m", f"Publish validated Colab notebook {args.public_id}")
        git("push", "origin", "main")
        remote_head = git("ls-remote", "origin", "refs/heads/main").split()[0]
        if remote_head != git("rev-parse", "HEAD"):
            fail("Push returned but origin/main does not match the local publication commit")
        print(f"Published: https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/{args.public_id}.ipynb")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    render_parser = sub.add_parser("render", help="Regenerate README and summary card from publication.json")
    render_parser.add_argument("--check", action="store_true")
    pub = sub.add_parser("publish", help="Publish an executed, validated notebook")
    pub.add_argument("--public-id", required=True)
    pub.add_argument("--run-dir", required=True, type=Path)
    pub.add_argument("--executed-output", required=True, type=Path)
    pub.add_argument("--cli-log", required=True, type=Path)
    pub.add_argument("--compute", required=True, choices=["CPU", "T4 GPU", "CPU + T4 GPU"])
    pub.add_argument("--validated-on", required=True)
    pub.add_argument("--demonstration", required=True)
    pub.add_argument("--preview-index", required=True, type=int)
    pub.add_argument("--preview-caption", required=True)
    pub.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.command == "render":
        data = load_manifest()
        generated = render(data)
        if args.check:
            if README.read_text(encoding="utf-8") != generated:
                fail("README is out of sync with publication.json")
            if not SUMMARY.is_file() or SUMMARY.read_text(encoding="utf-8") != render_summary(data):
                fail("Summary card is out of sync with publication.json")
            print(f"README and summary card match {len(data['notebooks'])} manifest entries")
        else:
            README.write_text(generated, encoding="utf-8")
            write_summary(data)
            print(f"Rendered {len(data['notebooks'])} entries")
    else:
        publish(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"publication error: {exc}", file=sys.stderr)
        sys.exit(1)
