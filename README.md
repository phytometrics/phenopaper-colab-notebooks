# PhenoPaper Colab notebooks

Execution-verified Google Colab demonstrations for selected plant phenotyping papers. Each notebook runs a small, documented part of the paper’s workflow; a successful example run does not establish paper-wide performance or reproduce every experiment.

公開論文の解析手順を小さな例で実行できる Colab ノートブックです。各ノートブックに実行範囲、出典、制約を記載しています。

## Notebooks

Notebook filenames use the paper’s PhenoPaper `public_id`. The paper link opens its individual PhenoPaper page; the Colab link opens the notebook directly. Semantic tags below are copied from the corresponding PhenoPaper record.

### NeuraLeaf: Disentangled Neural Parametric Modeling of Leaf Shape, Deformation, and Appearance

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-744d06547d0cf81dc008f601a6fe839c) · [DOI](https://doi.org/10.1007/s11263-026-03024-6) (`p-744d06547d0cf81dc008f601a6fe839c`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-744d06547d0cf81dc008f601a6fe839c.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-744d06547d0cf81dc008f601a6fe839c.ipynb)
- **Verified runtime:** T4 GPU · 2026-09-26
- **Demonstration:** Base-shape generation, deformation transfer/interpolation, and one fitting round-trip on a deterministic example. Partial: appearance modeling and dataset-level benchmarks are outside this run; the notebook documents the conference/journal version relationship.
- **Semantic tags (PhenoPaper):** `modality:rgbd`, `organ:leaf`, `task:morphology`, `task:reconstruction`, `trait:leaf_traits`

### Seed Morphology in Key Spanish Grapevine Cultivars

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-02f6f83e31a71dc69ce32db56b013ca3) · [DOI](https://doi.org/10.20944/preprints202103.0578.v1) (`p-02f6f83e31a71dc69ce32db56b013ca3`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-02f6f83e31a71dc69ce32db56b013ca3.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-02f6f83e31a71dc69ce32db56b013ca3.ipynb)
- **Verified runtime:** CPU · 2026-09-27
- **Demonstration:** Measures seed morphology and computes the J-index for Albillo Real (30 seeds), with comparison to paper reference values. Single-cultivar demonstration; a scale-calibration discrepancy is reported.
- **Semantic tags (PhenoPaper):** `crop:grapevine`, `organ:seed`, `task:classification`, `task:morphology`, `trait:reproductive_traits`

### 3D sorghum reconstructions from depth images enable identification of quantitative trait loci regulating shoot architecture

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-076a5cd5ebdeed1a9ffaf2ec05b49074) · [DOI](https://doi.org/10.1101/062174) (`p-076a5cd5ebdeed1a9ffaf2ec05b49074`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-076a5cd5ebdeed1a9ffaf2ec05b49074.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-076a5cd5ebdeed1a9ffaf2ec05b49074.ipynb)
- **Verified runtime:** CPU · 2026-09-27
- **Demonstration:** Runs the authors’ QTL-mapping analysis and compares results with their stored outputs. Partial: depth-image acquisition and 3D reconstruction are documented but not executed.
- **Semantic tags (PhenoPaper):** `crop:sorghum`, `environment:greenhouse`, `modality:rgbd`, `organ:leaf`, `organ:seed`, `organ:whole_plant`, `task:morphology`, `task:reconstruction`, `task:segmentation`, `trait:architecture`, `trait:leaf_traits`, `trait:plant_height`

### Looking behind occlusions: A study on amodal segmentation for robust on-tree apple fruit size estimation

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-0e108836e8a4514b8486db589101c1d8) · [DOI](https://doi.org/10.1016/j.compag.2023.107854) (`p-0e108836e8a4514b8486db589101c1d8`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-0e108836e8a4514b8486db589101c1d8.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-0e108836e8a4514b8486db589101c1d8.ipynb)
- **Verified runtime:** CPU and T4 GPU · 2026-09-27
- **Demonstration:** Runs amodal segmentation and fruit-diameter estimation on two author demo images. Both runtime paths were validated; the saved outputs use CPU. This is not a test-set performance evaluation.
- **Semantic tags (PhenoPaper):** `crop:apple`, `environment:field`, `modality:rgbd`, `organ:fruit`, `task:morphology`, `task:segmentation`, `trait:reproductive_traits`

### Deep aerenchyma: a transformer-based pipeline for scalable phenotyping of rice root aerenchyma lacunae across environments.

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-0f6c6d73a489f456dd530c51fce2b6f8) · [DOI](https://doi.org/10.1186/s13007-026-01546-1) (`p-0f6c6d73a489f456dd530c51fce2b6f8`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-0f6c6d73a489f456dd530c51fce2b6f8.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-0f6c6d73a489f456dd530c51fce2b6f8.ipynb)
- **Verified runtime:** CPU · 2026-09-27
- **Demonstration:** Runs the released rice-root aerenchyma inference workflow on three demo images and displays masks and measurements. Not a multi-environment dataset-scale evaluation.
- **Semantic tags (PhenoPaper):** `crop:rice`, `organ:root`, `organ:tissue`, `task:morphology`, `task:segmentation`, `trait:root_architecture`

### DeepStomata: Facial Recognition Technology for Automated Stomatal Aperture Measurement

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-4471692ed96241966f8a065745f5ce8b) · [DOI](https://doi.org/10.1101/365098) (`p-4471692ed96241966f8a065745f5ce8b`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-4471692ed96241966f8a065745f5ce8b.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-4471692ed96241966f8a065745f5ce8b.ipynb)
- **Verified runtime:** CPU · 2026-09-26
- **Demonstration:** Processes one author-provided image through stomata detection, four-class classification, and aperture measurement. Full 11-image example batch and paper-level performance are not claimed.
- **Semantic tags (PhenoPaper):** `organ:stomata`, `task:classification`, `task:object_detection`, `task:segmentation`, `trait:stomatal_traits`

### Operational Framework for Field-Scale Crop Sowing and Emergence Date Estimation Using Daily Synthetic Harmonized Landsat Sentinel-2 Time Series

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-cac607b350005b99ef850fe315328b02) · [DOI](https://doi.org/10.34133/remotesensing.0878) (`p-cac607b350005b99ef850fe315328b02`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-cac607b350005b99ef850fe315328b02.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-cac607b350005b99ef850fe315328b02.ipynb)
- **Verified runtime:** CPU · 2026-09-26
- **Demonstration:** Runs the crop sowing/emergence workflow for one site-year (`goodwaterbau`, 2023), including vegetation-index time series, gap filling, and stage/date estimation. Not a multi-site reproduction.
- **Semantic tags (PhenoPaper):** `crop:maize`, `crop:soybean`, `environment:field`, `modality:spectral`, `organ:whole_plant`, `task:time_series`, `trait:growth_development`

### FQGR-net: Morphology-based litchi flower quantification and gender recognition.

- **Paper:** [PhenoPaper paper page](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-3f9aa46c732dc37158c82721d4b77927) · [DOI](https://doi.org/10.1016/j.plaphe.2026.100217) (`p-3f9aa46c732dc37158c82721d4b77927`)
- **Notebook:** [Open in Colab](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-3f9aa46c732dc37158c82721d4b77927.ipynb) · [View source](https://github.com/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/p-3f9aa46c732dc37158c82721d4b77927.ipynb)
- **Verified runtime:** T4 GPU · 2026-09-27
- **Demonstration:** Runs the authors’ pretrained FQGR-Net on two author-provided validation samples and compares predicted counts with annotations. Not the 1,150-image benchmark; the code repository does not declare a license, as noted in the notebook.
- **Semantic tags (PhenoPaper):** `environment:field`, `organ:flower`, `task:classification`, `task:counting`, `trait:reproductive_traits`

## Validation and limitations

Each published notebook contains saved outputs from a recorded Colab run, with its pinned sources, input/output description, adaptations, and limitations. The demonstrations are intentionally scoped examples. Runtime availability and package compatibility can change, and AI-generated content is not guaranteed to be error-free.

各ノートブックに、保存済みの実行結果、出典、入力・出力、変更点、制約を記録しています。Colab の実行環境は変化するため、同じ結果が常に得られることを保証するものではありません。

## Publishing a new notebook

1. Use the PhenoPaper paper record and preserve its `public_id`; keep Paper, Tool, Repository, and Evidence provenance distinct.
2. Inspect and pin the source revision, model/data assets, and their licenses. Keep credentials out of notebooks and commits.
3. Build a self-contained notebook and state exactly which part of the method it demonstrates.
4. Run all cells on a fresh Colab runtime. Inspect the saved outputs, errors, and generated result files.
5. Publish as `notebooks/{public_id}.ipynb`, test the final Colab URL, and add a README entry.

The detailed workflow is maintained in the [PhenoPaper pipeline guide](https://github.com/phytometrics/phenocode-atlas/blob/main/docs/verified-colab-notebook-pipeline.md). Notebook publication does not approve a Paper, Tool, or Repository for the PhenoPaper Catalog; catalog records are reviewed separately.

## Sources and rights

Each notebook identifies its paper, implementation, pinned revision, asset provenance, and known license or reuse limitations. Check those upstream terms before reusing code, weights, images, or paper content. No PhenoPaper API key is needed to run a published notebook.
