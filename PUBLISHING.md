# Publishing a new notebook

1. Use the PhenoPaper paper record and preserve its `public_id`; keep Paper, Tool, Repository, and Evidence provenance distinct.
2. Inspect and pin the source revision, model/data assets, and their licenses. Keep credentials out of notebooks and commits.
3. Build a self-contained notebook and state exactly which part of the method it demonstrates.
4. Run all cells on a fresh Colab runtime. Inspect saved outputs, errors, and generated result files.
5. Run `tools/publication.py publish` from the persistent DGX checkout. It validates the saved notebook and archived Colab result, updates the single `publication.json`, extracts a preview from a saved PNG output, regenerates the README table and summary card, commits, and pushes. See the command example below.

The README summary card (`assets/notebook-summary.svg`), its accessible notebook count, and the table between the marker comments are generated from [`publication.json`](publication.json). Edit the manifest for metadata corrections, then run `python3 tools/publication.py render`. The card counts the manifest’s unique published notebooks, regardless of runtime type. Every successful publication updates and commits the card automatically; no external badge service or scheduled job is needed. Do not edit the SVG, summary block, or table rows by hand. A successful publication requires GitHub authentication in the process environment or `gh auth` configuration. Failed or code-only runs stay in the DGX run directory and are not published.

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

## Unverified references

The operator authorizes automatic publication of partial/incomplete notebooks using `python3 tools/publish_unverified.py publish --public-id PUBLIC_ID --run-dir RUN_DIR --status failed --reason REASON`. This only reads notebook JSON and never executes scientific code. It clears outputs in the published draft, adds an opening notice, preserves the original DGX run, and updates `unverified.json` and `UNVERIFIED.md`. It does not update `publication.json` or the execution-verified SVG count. No manual login validation is performed. Papers with no authored code get an attempt reason in PhenoPaper but no placeholder notebook. Every failed queue outcome is also added to [`FAILED.md`](FAILED.md), with the recorded reason and a PhenoPaper link; a draft link appears only when a notebook exists. `failures.json` is the source for that page and is updated by the queue publisher. Only a later fresh verified execution can promote a notebook into the verified manifest; historical draft files remain reference artifacts.
