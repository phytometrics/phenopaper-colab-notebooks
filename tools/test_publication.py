import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publication


class PublicationTests(unittest.TestCase):
    def test_bibliography_escapes_metadata_and_precedes_public_id(self):
        entry = dict(publication.load_manifest()["notebooks"][0])
        entry.update(journal="Journal | <test>", authors=["A <Author>"])
        rendered = publication.row(entry)
        self.assertIn("Journal &#124; &lt;test&gt;", rendered)
        self.assertIn("A &lt;Author&gt;", rendered)
        self.assertLess(rendered.index("Journal:"), rendered.index("Authors:"))
        self.assertLess(rendered.index("Authors:"), rendered.index("public_id:"))
        self.assertEqual(publication.author_names([{"given": "Ada", "family": "Lovelace"}]), ["Ada Lovelace"])
        self.assertIn("Journal not supplied", publication.bibliography({}))
        self.assertIn("Authors not supplied", publication.bibliography({}))

    def test_current_catalog_renders_from_publication_json(self):
        data = publication.load_manifest()
        self.assertGreater(len(data["notebooks"]), 0)
        self.assertEqual(publication.render(data), publication.README.read_text(encoding="utf-8"))
        self.assertEqual(publication.render_montage(data), publication.MONTAGE.read_bytes())

    def test_readme_index_links_every_notebook_directly(self):
        data = publication.load_manifest()
        index = publication.render_notebook_index(data)
        found = __import__('re').findall(r'\]\(notebooks/(p-[0-9a-f]+)\.ipynb\)', index)
        expected = [e["public_id"] for e in sorted(data["notebooks"], key=lambda e: (e["title"].casefold(), e["public_id"]))]
        self.assertEqual(found, expected)
        self.assertIn("<details>", index)
        self.assertIn("</details>", index)
        self.assertNotIn("<details open", index)
        for public_id in expected:
            self.assertIn(f"blob/main/notebooks/{public_id}.ipynb", index)

    def test_paginated_catalog_preserves_every_notebook_and_preview(self):
        data = publication.load_manifest()
        pages = publication.render_catalog(data)
        found = []
        for content in pages.values():
            self.assertLessEqual(len(content.encode("utf-8")), publication.CATALOG_PAGE_BYTE_LIMIT)
            self.assertIn('src="../assets/previews/', content)
            found.extend(__import__('re').findall(r'public_id: <code>(p-[0-9a-f]+)</code>', content))
        expected = [e["public_id"] for e in sorted(data["notebooks"], key=lambda e: (e["title"].casefold(), e["public_id"]))]
        self.assertEqual(found, expected)
        publication.sync_catalog(data, check=True)
        self.assertLess(len(publication.render(data).encode("utf-8")), publication.MARKDOWN_BYTE_LIMIT)

    def test_large_catalog_is_split_by_utf8_bytes(self):
        entry = dict(publication.load_manifest()["notebooks"][0])
        entries = [dict(entry, public_id=f"p-{i:032x}", demonstration="あ" * 4000) for i in range(100)]
        pages = publication.render_catalog({"notebooks": entries})
        self.assertGreater(len(pages), 2)
        self.assertTrue(all(len(p.encode("utf-8")) <= publication.CATALOG_PAGE_BYTE_LIMIT for p in pages.values()))
        self.assertEqual(sum(p.count('public_id: <code>') for p in pages.values()), 100)

    def test_montage_selects_up_to_96_recent_real_previews(self):
        entries = [
            {"public_id": f"p-{index:032x}", "validated_on": f"2026-10-{index:03d}"}
            for index in range(118)
        ]
        with patch("publication.has_real_preview", return_value=True):
            selected = publication.select_montage_entries(entries)
        self.assertEqual(len(selected), 96)
        self.assertEqual(selected[0]["public_id"], entries[-1]["public_id"])
        self.assertEqual(selected[-1]["public_id"], entries[-96]["public_id"])

    def test_montage_grid_expands_for_96_tiles_and_fits_canvas(self):
        columns, rows, tile_width, tile_height = publication.montage_layout(96)
        self.assertEqual((columns, rows), (12, 8))
        self.assertGreaterEqual(tile_width, 80)
        self.assertGreaterEqual(tile_height, 50)
        self.assertLessEqual(columns * tile_width + (columns - 1) * 8, 1200 - 48)
        self.assertLessEqual(rows * tile_height + (rows - 1) * 8, 630 - 112 - 20)

    def test_preview_from_line_wrapped_notebook_output(self):
        notebook = {"cells": [{"cell_type": "code", "outputs": [
            {"data": {"image/png": "iVBORw0KGgo=\n"}}
        ]}]}
        self.assertEqual(publication.get_preview(notebook, 0), publication.PNG_MAGIC)

    def test_notebook_with_error_output_is_rejected(self):
        notebook = {
            "nbformat": 4,
            "cells": [
                {"cell_type": "markdown", "source": ["This cell checks error handling."]},
                {"cell_type": "code", "source": ["raise RuntimeError()"],
                 "outputs": [{"output_type": "error", "ename": "RuntimeError", "evalue": ""}]},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.ipynb"
            path.write_text(json.dumps(notebook), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "error output"):
                publication.check_notebook(path)

    def test_public_id_and_metadata_must_be_safe(self):
        entry = dict(publication.load_manifest()["notebooks"][0])
        entry["public_id"] = "../../wrong"
        with self.assertRaisesRegex(ValueError, "Invalid public_id"):
            publication.validate_entry(entry)
        entry = dict(publication.load_manifest()["notebooks"][0])
        entry["demonstration"] = "bad | table"
        with self.assertRaisesRegex(ValueError, "table-breaking"):
            publication.validate_entry(entry)

    def test_title_cannot_break_markdown_link(self):
        entry = dict(publication.load_manifest()["notebooks"][0])
        entry["title"] = "A [linked] title"
        self.assertIn("A \\[linked\\] title", publication.row(entry))


if __name__ == "__main__":
    unittest.main()
