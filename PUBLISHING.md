# Publishing a new notebook

1. Use the PhenoPaper paper record and preserve its `public_id`; keep Paper, Tool, Repository, and Evidence provenance distinct.
2. Inspect and pin the source revision, model/data assets, and their licenses. Keep credentials out of notebooks and commits.
3. Build a self-contained notebook and state exactly which part of the method it demonstrates.
4. Run all cells on a fresh Colab runtime. Inspect saved outputs, errors, and generated result files.
5. Run `tools/publication.py publish` from the persistent DGX checkout. It validates the saved notebook and archived Colab result, updates the single `publication.json`, extracts a preview from a saved PNG output, regenerates this table, commits, and pushes. See the command example below.

The table between the marker comments is generated from [`publication.json`](publication.json). Edit the manifest for metadata corrections, then run `python3 tools/publication.py render`. Do not edit the table rows by hand. A successful publication requires GitHub authentication in the process environment or `gh auth` configuration. Failed or code-only runs stay in the DGX run directory and are not published.

```bash
python3 tools/publication.py publish \
  --public-id p-... \
  --run-dir /home/phyto/phenotyping-colab/runs/RUN_NAME \
  --executed-output /home/phyto/phenotyping-colab/runs/RUN_NAME/logs/final_output.ipynb \
  --cli-log /home/phyto/phenotyping-colab/runs/RUN_NAME/logs/final_session.md \
  --compute CPU --validated-on YYYY-MM-DD \
  --demonstration "Short, evidence-backed scope and limitation." \
  --preview-index 0 --preview-caption "What the saved result shows"
```

Notebook publication does not approve a Paper, Tool, or Repository for the PhenoPaper Catalog; catalog records are reviewed separately.
