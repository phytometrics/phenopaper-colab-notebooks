#!/usr/bin/env python3
"""Publish validated Colab notebooks and render README from publication.json.

Only notebook JSON and its saved PNG outputs are read. Notebook code is never run.
"""

from __future__ import annotations

import argparse
import generation
import base64
import binascii
import datetime as dt
import fcntl
import html
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "publication.json"
README = REPO / "README.md"
SUMMARY = REPO / "assets" / "notebook-summary.svg"
MONTAGE = REPO / "assets" / "notebook-montage.png"
SUMMARY_START = "<!-- publication-summary:start -->"
SUMMARY_END = "<!-- publication-summary:end -->"
START = "<!-- publication-table:start -->"
END = "<!-- publication-table:end -->"
INDEX_START = "<!-- notebook-index:start -->"
INDEX_END = "<!-- notebook-index:end -->"
PUBLIC_ID = re.compile(r"p-[a-f0-9]{32}\Z")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_PREVIEW_BYTES = 8_000_000
MAX_MONTAGE_TILES = 96
MAX_MONTAGE_COLUMNS = 16
MUTATION_HEAD: str | None = None


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
    generation.validate(entry.get("generation"))
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
    details = f"**{title}**<br><sub>public_id: <code>{public_id}</code></sub><br><br>"
    details += f"[![Open in PhenoPaper](https://img.shields.io/badge/Open_in-PhenoPaper-356859?style=flat-square)]({paper}) "
    if entry.get("doi"):
        details += f"[![DOI paper](https://img.shields.io/badge/DOI-paper-326CE5?style=flat-square)](https://doi.org/{quote(entry['doi'], safe='/')}) "
    details += f"[![Open in Colab](https://img.shields.io/badge/Open_in-Colab-F9AB00?style=flat-square&logo=googlecolab&logoColor=white)]({colab}) "
    compute = entry["compute"]
    badge = {"CPU": ("CPU", "lightgrey"), "T4 GPU": ("T4%20GPU", "blue"), "CPU + T4 GPU": ("CPU%20%2B%20T4%20GPU", "purple")}[compute]
    details += f"[![Compute: {compute}](https://img.shields.io/badge/compute-{badge[0]}-{badge[1]}?style=flat-square)]({colab}) "
    date_badge = entry["validated_on"].replace("-", "--")
    details += f"![Validated {entry['validated_on']}](https://img.shields.io/badge/validated-{date_badge}-6c757d?style=flat-square) "
    details += "<br><sub><b>Generated with:</b> " + html.escape(generation.summary(entry.get("generation"))) + "</sub>"
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
  <desc id="description">{count} AI-verified notebooks</desc>
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
    <text x="{label_x}" y="154" fill="#f1f6ed" font-size="21" font-weight="600" letter-spacing="2">AI-VERIFIED</text>
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


def has_real_preview(entry: dict) -> bool:
    """Reject missing/placeholder previews and images with no visible content."""
    preview = entry.get("preview")
    if not isinstance(preview, dict):
        return False
    caption = str(preview.get("caption", "")).casefold()
    if "no image or graph generated" in caption or "placeholder" in caption:
        return False
    path = REPO / "assets" / "previews" / f"{entry['public_id']}.png"
    try:
        with Image.open(path) as source:
            if source.format != "PNG" or source.width < 32 or source.height < 32:
                return False
            if source.width * source.height > 50_000_000:
                return False
            source.load()
            rgba = ImageOps.exif_transpose(source).convert("RGBA")
        # Composite transparency onto the same light background used by the tiles.
        background = Image.new("RGBA", rgba.size, (247, 248, 244, 255))
        background.alpha_composite(rgba)
        sample = background.convert("RGB")
        sample.thumbnail((32, 32), Image.Resampling.LANCZOS)
        detail_pixels = sum(1 for pixel in sample.getdata() if min(pixel) < 242)
        variation = sum(ImageStat.Stat(sample).stddev) / 3
        return detail_pixels >= 2 and variation >= 1.0
    except (OSError, ValueError, Image.DecompressionBombError):
        return False


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def select_montage_entries(entries: list[dict], limit: int = MAX_MONTAGE_TILES) -> list[dict]:
    """Choose recent verified previews while keeping the README montage bounded."""
    ordered = sorted(
        entries,
        key=lambda entry: (entry["validated_on"], entry["public_id"]),
        reverse=True,
    )
    return [entry for entry in ordered if has_real_preview(entry)][:limit]


def montage_layout(count: int, width: int = 1200, height: int = 630) -> tuple[int, int, int, int]:
    """Return a compact column/row layout that uses the montage canvas efficiently."""
    if count < 1:
        fail("Montage layout requires at least one preview")
    columns = min(
        count,
        MAX_MONTAGE_COLUMNS,
        max(1, math.ceil(math.sqrt(count * 1.5))),
    )
    rows = math.ceil(count / columns)
    margin_x, gap, grid_top, margin_bottom = 24, 8, 112, 20
    tile_width = (width - 2 * margin_x - (columns - 1) * gap) // columns
    tile_height = (height - grid_top - margin_bottom - (rows - 1) * gap) // rows
    return columns, rows, tile_width, tile_height


def render_montage(data: dict) -> bytes:
    """Build a wide README hero from up to 96 recent, nonblank verified previews."""
    selected = select_montage_entries(data["notebooks"])
    if not selected:
        fail("No nonblank AI-verified notebook previews are available for the README montage")

    width, height = 1200, 630
    canvas = Image.new("RGB", (width, height), "#0c2c24")
    draw = ImageDraw.Draw(canvas)
    top = (20, 62, 48)
    bottom = (8, 34, 29)
    for y in range(height):
        blend = y / max(1, height - 1)
        color = tuple(round(top[c] * (1 - blend) + bottom[c] * blend) for c in range(3))
        draw.line((0, y, width, y), fill=color)
    draw.ellipse((1015, -185, 1375, 175), fill=(27, 83, 62))
    draw.ellipse((1060, -132, 1345, 153), outline=(68, 123, 91), width=2)

    draw.rounded_rectangle((26, 22, 43, 61), radius=8, fill=(173, 214, 154))
    draw.ellipse((24, 24, 38, 42), fill=(173, 214, 154))
    draw.ellipse((32, 38, 46, 56), fill=(133, 185, 135))
    draw.text((58, 22), "PhenoPaper  ×  Google Colab", font=load_font(31, bold=True), fill="#f2f6ef")
    draw.text((60, 66), "PLANT PHENOTYPING REPRODUCTIONS", font=load_font(13, bold=True), fill="#a9c5b0")
    count = f"{len(data['notebooks']):,}"
    count_font = load_font(39, bold=True)
    count_box = draw.textbbox((0, 0), count, font=count_font)
    count_width = count_box[2] - count_box[0]
    draw.text((width - 33 - count_width, 16), count, font=count_font, fill="#ffffff")
    draw.text((width - 34, 65), "AI-VERIFIED NOTEBOOKS", font=load_font(13, bold=True), fill="#c9d8ca", anchor="ra")

    columns, _rows, tile_width, tile_height = montage_layout(len(selected), width, height)
    gap, grid_top = 8, 112
    for index, entry in enumerate(selected):
        row_index, col_index = divmod(index, columns)
        row_count = min(columns, len(selected) - row_index * columns)
        row_width = row_count * tile_width + (row_count - 1) * gap
        x = (width - row_width) // 2 + col_index * (tile_width + gap)
        y = grid_top + row_index * (tile_height + gap)
        path = REPO / "assets" / "previews" / f"{entry['public_id']}.png"
        with Image.open(path) as source:
            source.load()
            rgba = ImageOps.exif_transpose(source).convert("RGBA")
            opaque = Image.new("RGBA", rgba.size, (247, 248, 244, 255))
            opaque.alpha_composite(rgba)
            tile = ImageOps.fit(
                opaque.convert("RGB"),
                (tile_width, tile_height),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        mask = Image.new("L", tile.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, tile_width - 1, tile_height - 1), radius=7, fill=255)
        canvas.paste(tile, (x, y), mask)
        draw.rounded_rectangle((x, y, x + tile_width - 1, y + tile_height - 1), radius=7, outline=(135, 170, 143), width=1)

    output = io.BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


def write_montage(data: dict) -> None:
    MONTAGE.parent.mkdir(parents=True, exist_ok=True)
    MONTAGE.write_bytes(render_montage(data))


# Leave ample room below GitHub's 500 KiB README rendering limit.
MARKDOWN_BYTE_LIMIT = 400_000
CATALOG_PAGE_BYTE_LIMIT = 200_000
TABLE_HEADER = "| Paper and run details | Preview |\n| --- | --- |"


def catalog_groups(data: dict) -> list:
    entries = sorted(data["notebooks"], key=lambda e: (e["title"].casefold(), e["public_id"]))
    groups, page, size, start = [], [], 0, 0
    for entry in entries:
        entry_size = len(row(entry).encode("utf-8")) + 1
        if entry_size > CATALOG_PAGE_BYTE_LIMIT - 10_000:
            fail("Notebook metadata exceeds the catalog page size budget")
        if page and (len(page) >= 50 or size + entry_size > CATALOG_PAGE_BYTE_LIMIT - 10_000):
            groups.append((len(groups) + 1, start, page))
            start += len(page)
            page, size = [], 0
        page.append(entry)
        size += entry_size
    if page:
        groups.append((len(groups) + 1, start, page))
    return groups


def render_catalog(data: dict) -> dict:
    groups = catalog_groups(data)
    pages = {}
    for number, start, entries in groups:
        navigation = ["[README / notebook index](../README.md#notebooks)"]
        if number > 1:
            navigation.append(f"[Previous](page-{number - 1:03d}.md)")
        if number < len(groups):
            navigation.append(f"[Next](page-{number + 1:03d}.md)")
        text = "\n\n".join([
            f"# Notebook catalog — page {number} of {len(groups)}",
            " · ".join(navigation),
            f"Alphabetical entries {start + 1}–{start + len(entries)} of {len(data['notebooks'])}. "
            "Generated from publication.json; includes generation conditions and execution previews.",
            TABLE_HEADER + "\n" + "\n".join(row(e).replace('src="assets/', 'src="../assets/') for e in entries),
            " · ".join(navigation),
        ]) + "\n"
        if len(text.encode("utf-8")) > CATALOG_PAGE_BYTE_LIMIT:
            fail("Catalog page exceeds the Markdown size budget")
        pages[f"page-{number:03d}.md"] = text
    return pages


def sync_catalog(data: dict, check: bool = False) -> None:
    directory = REPO / "catalog"
    pages = render_catalog(data)
    existing = set(p.name for p in directory.glob("page-*.md"))
    if check:
        if existing != set(pages) or any((directory / name).read_text(encoding="utf-8") != content for name, content in pages.items()):
            fail("Catalog pages are out of sync with publication.json")
        return
    directory.mkdir(exist_ok=True)
    for name, content in pages.items():
        (directory / name).write_text(content, encoding="utf-8")
    for name in existing - set(pages):
        (directory / name).unlink()


def render_notebook_index(data: dict) -> str:
    entries = sorted(data["notebooks"], key=lambda entry: (entry["title"].casefold(), entry["public_id"]))
    items = []
    for entry in entries:
        public_id = entry["public_id"]
        title = html.escape(entry["title"]).replace(chr(92), chr(92) * 2).replace("[", chr(92) + "[").replace("]", chr(92) + "]")
        notebook = f"notebooks/{public_id}.ipynb"
        colab = f"https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/{notebook}"
        items.append(f"- [{title}]({notebook}) · [Open in Colab]({colab})")
    catalog_links = [
        f"- [Page {number}: notebooks {start + 1}–{start + len(page)}](catalog/page-{number:03d}.md)"
        for number, start, page in catalog_groups(data)
    ]
    if not items:
        items.append("- No AI-verified notebooks have been published yet.")

    links = [
        "- [Notebook index](#notebook-index)",
        "- [Failed attempts](FAILED.md)",
        "- [Unverified and incomplete notebooks](UNVERIFIED.md)",
    ]
    if (REPO / "PARTIALLY_VERIFIED.md").is_file():
        links.insert(2, "- [Partially AI-verified notebooks](PARTIALLY_VERIFIED.md)")
    links.extend([
        "- [Validation and limitations](#validation-and-limitations)",
        "- [Maintainers](#maintainers)",
        "- [Sources and rights](#sources-and-rights)",
    ])
    count = len(entries)
    return "\n".join([
        "## Contents",
        "",
        *links,
        "",
        "### Notebook index",
        "",
        f"Browse all {count} AI-verified notebooks alphabetically:",
        "",
        *items,
        "",
        "#### Detailed catalog with previews",
        "",
        *catalog_links,
        "",
    ])


def render(data: dict) -> str:
    current = README.read_text(encoding="utf-8")
    current = re.sub(r"(?m)^Each row starts with an Open in PhenoPaper badge[^\n]*\n\n", "", current)
    if current.count(START) != 1 or current.count(END) != 1:
        fail("README must contain exactly one publication-table marker pair")
    if current.count(SUMMARY_START) != 1 or current.count(SUMMARY_END) != 1:
        fail("README must contain exactly one publication-summary marker pair")
    if current.count(INDEX_START) != 1 or current.count(INDEX_END) != 1:
        fail("README must contain exactly one notebook-index marker pair")
    count = len(data["notebooks"])
    before_summary, summary_rest = current.split(SUMMARY_START, 1)
    _, after_summary = summary_rest.split(SUMMARY_END, 1)
    card = f'<p align="center"><a href="#notebooks"><img src="assets/notebook-montage.png" width="100%" alt="PhenoPaper × Google Colab — {count} AI-verified notebooks" /></a></p>'
    current = before_summary + SUMMARY_START + "\n" + card + "\n" + SUMMARY_END + after_summary
    before, rest = current.split(INDEX_START, 1)
    _, after = rest.split(INDEX_END, 1)
    index = render_notebook_index(data)
    current = before + INDEX_START + "\n" + index + "\n" + INDEX_END + after
    recent = list(reversed(data["notebooks"]))[:2]
    table = f"Showing the {len(recent)} most recently published notebooks of {count}. " + "[Browse the complete alphabetical catalog](#notebook-index)."
    if recent:
        table += "\n\n" + TABLE_HEADER + "\n" + "\n".join(row(entry) for entry in recent)
    before, rest = current.split(START, 1)
    _, after = rest.split(END, 1)
    result = before + START + "\n\n" + table + "\n\n" + END + after
    if len(result.encode("utf-8")) > MARKDOWN_BYTE_LIMIT:
        fail("README exceeds its Markdown size budget")
    return result


def check_notebook(path: Path) -> dict:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        fail("Notebook is not valid nbformat 4 JSON")
    code_cells = [c for c in notebook["cells"] if c.get("cell_type") == "code"]
    if not code_cells:
        fail("Notebook has no code cells")
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            previous = notebook["cells"][index - 1] if index else None
            source = previous.get("source", []) if previous else []
            if isinstance(source, list): source = "".join(source)
            if not previous or previous.get("cell_type") != "markdown" or not source.strip():
                fail(f"Code cell {index + 1} has no explanatory Markdown predecessor")
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


def begin_mutation() -> None:
    global MUTATION_HEAD
    MUTATION_HEAD = git("rev-parse", "HEAD")


def finish_mutation() -> None:
    global MUTATION_HEAD
    MUTATION_HEAD = None


def rollback_mutation() -> None:
    """Restore a previously clean publication checkout after an interrupted write."""
    global MUTATION_HEAD
    if MUTATION_HEAD is None:
        return
    head = MUTATION_HEAD
    reset = subprocess.run(["git", "-C", str(REPO), "reset", "--hard", head], text=True, capture_output=True)
    clean = subprocess.run(["git", "-C", str(REPO), "clean", "-fd"], text=True, capture_output=True)
    if reset.returncode or clean.returncode:
        detail = (reset.stderr + clean.stderr).strip()[:600]
        raise RuntimeError("Could not restore publication checkout after an interrupted write: " + detail)
    MUTATION_HEAD = None


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
    cli_log = args.cli_log.read_text(encoding="utf-8")
    session_execution_count = len(re.findall(r"^### Execution\b", cli_log, re.M))
    cli_records = re.findall(r"^\[colab\] Executing cell (\d+)/(\d+) -", cli_log, re.M)
    cli_complete = (
        cli_records == [(str(index), str(code_count)) for index in range(1, code_count + 1)]
        and re.search(r"^\[colab\] Saving notebook with outputs to ", cli_log, re.M) is not None
    )
    if session_execution_count < code_count and not cli_complete:
        fail(f"CLI log has {session_execution_count} session executions and no complete ordered CLI record for {code_count} code cells")
    report = report_path.read_text(encoding="utf-8").lower()
    if any(term in report for term in ("code-only / not executed", "execution failed", "not validated")):
        fail("Report indicates notebook is unexecuted or failed")
    image = get_preview(result["notebook"], args.preview_index)
    entry = {
        "public_id": args.public_id,
        "generation": generation.for_run(run_dir),
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
        begin_mutation()
        data = load_manifest()
        existing = next((e for e in data["notebooks"] if e["public_id"] == args.public_id), None)
        target_notebook = REPO / "notebooks" / f"{args.public_id}.ipynb"
        target_preview = REPO / "assets" / "previews" / f"{args.public_id}.png"
        if existing and not args.replace:
            if target_notebook.read_bytes() == notebook_path.read_bytes():
                print(f"Already published: {args.public_id}")
                finish_mutation()
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
        sync_catalog(data)
        write_summary(data)
        write_montage(data)
        if (REPO / "unverified.json").exists():
            subprocess.run([sys.executable, str(REPO / "tools/publish_unverified.py"), "render"], check=True)
            git("add", "--", "unverified.json", "UNVERIFIED.md", "FAILED.md", "README.md")
        git("add", "--", str(target_notebook.relative_to(REPO)), str(target_preview.relative_to(REPO)), "publication.json", "README.md", "catalog", str(SUMMARY.relative_to(REPO)), str(MONTAGE.relative_to(REPO)))
        if not git("diff", "--cached", "--name-only"):
            print(f"Already up to date: {args.public_id}")
            finish_mutation()
            return
        git("commit", "-m", f"Publish validated Colab notebook {args.public_id}")
        git("push", "origin", "main")
        remote_head = git("ls-remote", "origin", "refs/heads/main").split()[0]
        if remote_head != git("rev-parse", "HEAD"):
            fail("Push returned but origin/main does not match the local publication commit")
        finish_mutation()
        print(f"Published: https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/{args.public_id}.ipynb")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    render_parser = sub.add_parser("render", help="Regenerate README images and index from publication.json")
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
            sync_catalog(data, check=True)
            if README.read_text(encoding="utf-8") != generated:
                fail("README is out of sync with publication.json")
            if not SUMMARY.is_file() or SUMMARY.read_text(encoding="utf-8") != render_summary(data):
                fail("Summary card is out of sync with publication.json")
            if not MONTAGE.is_file() or MONTAGE.read_bytes() != render_montage(data):
                fail("README montage is out of sync with publication.json previews")
            print(f"README and generated images match {len(data['notebooks'])} manifest entries")
        else:
            README.write_text(generated, encoding="utf-8")
            sync_catalog(data)
            write_summary(data)
            write_montage(data)
            print(f"Rendered {len(data['notebooks'])} entries")
    else:
        publish(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        try:
            rollback_mutation()
        except RuntimeError as rollback_error:
            print(str(rollback_error), file=sys.stderr)
        print(f"publication error: {exc}", file=sys.stderr)
        sys.exit(1)
