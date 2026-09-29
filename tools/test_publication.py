import json
from pathlib import Path
import tempfile
import unittest

import publication


class PublicationTests(unittest.TestCase):
    def test_existing_catalog_is_reproducible(self):
        data = publication.load_manifest()
        self.assertEqual(len(data["notebooks"]), 8)
        self.assertEqual(publication.render(data), publication.README.read_text(encoding="utf-8"))

    def test_preview_from_line_wrapped_notebook_output(self):
        notebook = {"cells": [{"cell_type": "code", "outputs": [
            {"data": {"image/png": "iVBORw0KGgo=\n"}}
        ]}]}
        self.assertEqual(publication.get_preview(notebook, 0), publication.PNG_MAGIC)

    def test_notebook_with_error_output_is_rejected(self):
        notebook = {
            "nbformat": 4,
            "cells": [{"cell_type": "code", "source": ["raise RuntimeError()"],
                       "outputs": [{"output_type": "error", "ename": "RuntimeError", "evalue": ""}]}],
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


if __name__ == "__main__":
    unittest.main()
