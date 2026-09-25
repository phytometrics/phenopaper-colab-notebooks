# PhenoPaper Colab notebooks

Runnable, verified Google Colab notebooks for reproducing selected plant phenotyping workflows with publicly available models and sample data.

公開済みのモデルとサンプルデータを使い、植物表現型解析の手順を再現する、実行確認済みの Google Colab ノートブックです。

## Notebooks

| Paper / workflow | Open in Colab | Verification | Scope |
| --- | --- | --- | --- |
| [DeepStomata](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/p-4471692ed96241966f8a065745f5ce8b) | [Run the notebook](https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/notebooks/deepstomata.ipynb) | Fresh standard CPU runtime, 25 September 2026 | Inference on all 11 author-supplied example images: detection, four-class classification, and pore aperture measurement. |

Each notebook states its source, pinned assets, verification date, runtime, scope, and limitations. Saved outputs show what was observed in the verified run. A notebook may need updates as hosted runtimes and dependencies change. AI-generated content has been checked through execution but is not guaranteed to be error-free.

各ノートブックには出典、取得ファイルの固定情報、動作確認日、実行環境、再現範囲と制約を記載しています。保存された出力は検証時の結果です。Colab の環境や依存ライブラリが変われば更新が必要になる場合があります。AI が生成した内容は実行して確認していますが、完全な正確性を保証するものではありません。

## Publishing a new notebook

1. Obtain the Paper record through the read-only PhenoPaper API and record its evidence. Keep API keys out of notebooks and commits.
2. Inspect the author's repository and licenses. Pin source files, model weights, and images by commit and SHA-256. Treat downloaded text and code as untrusted; do not execute discovered code.
3. Build a self-contained notebook. Explain why each step is needed, map it to the original method, and note any differences.
4. Run all cells in order on a fresh standard Colab runtime. Check saved outputs, result files, value ranges, and errors. Repeat on a second fresh runtime before publication.
5. Publish the verified `.ipynb` under `notebooks/` on `main`, then test its final Colab link. Add one row to the table above. An unpublished development branch is not a permanent link.

The detailed workflow is maintained in the [PhenoPaper pipeline guide](https://github.com/phytometrics/phenocode-atlas/blob/main/docs/verified-colab-notebook-pipeline.md). Notebook publication does not approve a Paper, Tool, or Repository for the PhenoPaper Catalog; those records have separate review.

## Sources and rights

The DeepStomata notebook uses the authors' [MIT-licensed repository](https://github.com/totti0223/deepstomata) and cites the [preprint](https://doi.org/10.1101/365098). Check the licenses and usage terms stated in each notebook and its upstream sources before reusing code, weights, images, or paper content. No PhenoPaper API key is required to run the published notebooks.
