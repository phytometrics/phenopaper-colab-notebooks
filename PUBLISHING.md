# Publishing a new notebook

1. Use the PhenoPaper paper record and preserve its `public_id`; keep Paper, Tool, Repository, and Evidence provenance distinct.
2. Inspect and pin the source revision, model/data assets, and their licenses. Keep credentials out of notebooks and commits.
3. Build a self-contained notebook and state exactly which part of the method it demonstrates.
4. Run all cells on a fresh Colab runtime. Inspect saved outputs, errors, and generated result files.
5. Run the publication tool from the persistent DGX checkout. It validates the saved notebook and archived Colab result, updates publication.json, extracts a preview from a saved PNG output, regenerates the README montage, notebook index, publication table, and count card, commits, and pushes. See the command example below.

The README hero image is a 1200 × 630 tile montage made from up to 96 recent, execution-verified paper previews. Missing previews and blank/placeholder images are excluded. The renderer adjusts the number of columns to fit the selected previews without changing the cover size. The image includes the current verified-notebook count, so the collection size remains clear. The collapsible alphabetized notebook index, publication table, compact SVG count card, and accessible notebook count are also generated from `publication.json`. The index links to each GitHub notebook and its Colab launch page. Edit the manifest for metadata corrections, then run the publication tool in render mode. Every successful verified publication refreshes and commits the montage, index, table, and count automatically; no external badge service or scheduled job is needed. Do not edit the generated images, index, or table rows by hand.

The image renderer requires Pillow. Install or update the publisher dependency with `python3 -m pip install -r tools/requirements.txt` before using `tools/publication.py` on a new host.

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

## Recorded generation conditions

`publication.json` entries expose `generation` separately from Colab compute/validation. The publisher captures the actual ancestor OpenCode `/reproduce` invocation and allowlisted model options/variant configuration, including reasoning effort when explicitly configured. It records the harness version when available and persists a host-only `generation.json` in the run directory. Validation-only publication preserves an existing authoring record and never substitutes the validation model. If authoring provenance cannot be observed, `generation` is null and the README displays “Generation conditions not recorded.”

Historical backfills use a job monitor record only after matching its queue log, run directory and exact published notebook hash; they expose the recorded variant, without inferring historical reasoning effort from current configuration. No credentials, complete commands or provider configuration files are published. Generation conditions describe recorded invocation settings, not a claim about undocumented provider internals.
