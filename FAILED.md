# Failed attempts without a saved notebook

This page lists failed attempts that did not leave a saved draft notebook for reference. When a draft exists, the paper appears only on [Unverified and incomplete notebooks](UNVERIFIED.md), with its failure reason and Colab link. A failed attempt does not establish that the paper is irreproducible. Failure details are drawn from queue reports and captured tool diagnostics.

Notebook草稿を残せなかった失敗試行を掲載しています。草稿を保存できた論文は重複させず、未検証一覧に理由とColabリンクをまとめています。失敗は論文が再現不可能であることを意味しません。

[Execution-verified notebooks](README.md#notebooks) · [Unverified and incomplete notebooks](UNVERIFIED.md)

| Paper / record | Failed date / investigation run | Recorded failure reason |
| --- | --- | --- |
| **The shape and volume of air, kernels, and cracks, in a nutshell**<br>`p-ba13883f7b82cc94cac3648cf3a69310`<br>[PhenoPaper](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-ba13883f7b82cc94cac3648cf3a69310) | 2026-10-02<br>`p-ba13883f7b82cc94cac3648cf3a69310-20261002T014045Z` | The run planned a Colab-only probe because the PCA notebook is 2.13 MB and exceeds the DGX code-fetch cap. One fetch request used a .py path absent at the pinned commit (the source is a .ipynb); a diagnostic probe notebook was then authored, but Colab CPU allocation was refused. No completed reproduction notebook or queue-result was produced. The recorded OpenCode exit -10 does not identify which preceding issue terminated the overall run. |
| **KineticGP: a computational framework for genomic prediction of leaf photosynthesis traits**<br>`p-88d0f80b038259b9b4b2891d38bdcb0a`<br>[PhenoPaper](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-88d0f80b038259b9b4b2891d38bdcb0a) | 2026-10-02<br>`p-88d0f80b038259b9b4b2891d38bdcb0a-20260930T125150Z-3670543` | The recorded run fetched the paper metadata, then stopped before authoring a notebook or launching Colab. OpenCode auto-rejected a command that accessed the DGX host&#x27;s external /tmp directory; the run log does not establish that this rejection was the sole cause. No notebook or queue-result was produced, so this is an authoring/runner interruption, not a failed scientific execution. |
