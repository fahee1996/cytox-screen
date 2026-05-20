# Cytotoxicity Screening of Anticancer / ADC Payload Candidates

Predicts cytotoxicity of small molecules against **HepG2**, **human primary skeletal muscle cells (HSkMC)**, and **IMR-90** cell lines using pre-trained Chemprop ensembles from Wong et al. (2023).

This repository is a **derivative work** built on top of the published research code at [felixjwong/antibioticsai](https://github.com/felixjwong/antibioticsai). All deep-learning model code, training data, and trained checkpoints are from Wong et al. The original codebase is preserved here unchanged; this fork adds a thin prediction wrapper for batch-screening anticancer / ADC payload candidate libraries.

> **Credit.** The underlying models and Chemprop training code are the work of Felix J. Wong and co-authors. See [`UPSTREAM_README.md`](UPSTREAM_README.md) for the original documentation and cite the original paper below for any work that uses these models.
>
> Wong, F. et al. *Discovery of a structural class of antibiotics with explainable deep learning.* Nature (2023).

---

## What's new in this fork

| File | What it does |
|---|---|
| `run_cytox_pred.py` | Runs three cytotoxicity ensembles (HepG2, HSkMC, IMR-90) over a CSV of SMILES and appends predictions back into the input CSV. |
| `anticancer_unique.csv` | Example input: a curated set of anticancer / ADC payload candidates with metadata. Already populated with predictions from a previous run. |

Everything else (the `final_checkpoints/` ensembles, `working_example/`, `library_predictions/`, `notebooks/`, `LICENSE`) is unchanged from the upstream repository.

---

## Requirements

- Linux or WSL2 on Windows (tested on Ubuntu)
- [Conda](https://docs.conda.io/projects/miniconda/en/latest/) (Miniconda or Anaconda)
- ~5 GB free disk for the conda environment
- The `final_checkpoints/` directory containing trained models (not in this repo — see Setup step 3)
- Optional but recommended: an NVIDIA GPU with CUDA drivers. CPU works but each ensemble call takes longer.

---

## Setup (one time)

### 1. Clone this repository

```bash
git clone https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
cd <YOUR-REPO-NAME>
```

### 2. Create and activate the conda environment

```bash
conda create -n chemprop python=3.8 -y
conda activate chemprop
conda install -c conda-forge rdkit -y
pip install git+https://github.com/bp-kelley/descriptastorus
pip install chemprop
pip install pandas
```

Verify the install:

```bash
chemprop_predict --help
python -c "from rdkit import Chem; print(Chem.MolFromSmiles('CCO'))"
```

You should see Chemprop's CLI help and an `<rdkit.Chem.rdchem.Mol object at ...>` line.

### 3. Get the trained model checkpoints

The `.pt` checkpoint files are not committed (they are large and unchanged from upstream). Pull them from the original repository:

```bash
# From inside this repo's folder:
git clone https://github.com/felixjwong/antibioticsai.git _upstream
cp -r _upstream/final_checkpoints ./final_checkpoints
rm -rf _upstream
```

After this you should have:

```
final_checkpoints/
  antibiotic_no_betalactams/   model_1.pt … model_20.pt
  antibiotic_no_quinolones/    model_1.pt … model_20.pt
  antibiotic_staph/            model_1.pt … model_20.pt
  cytotox_hepg2/               model_1.pt … model_20.pt
  cytotox_primary/             model_1.pt … model_20.pt   ← used by run_cytox_pred.py as "hskmc"
  cytotox_imr90/               model_1.pt … model_20.pt
  pmf_staph/                   model_1.pt … model_20.pt
```

---

## How to run predictions (step by step)

### Inputs

Your input file must be a CSV with at least one column named **`smiles`** (lowercase). Other columns are passed through untouched.

Example minimal CSV:

```csv
smiles
CC(=O)Oc1ccccc1C(=O)O
CN1C=NC2=C1C(=O)N(C(=O)N2C)C
```

### Run

```bash
# 1. activate the environment
conda activate chemprop

# 2. cd into the repo
cd ~/cytox_Proj/antibioticsai     # or wherever you cloned it

# 3. make sure your input file is named anticancer_unique.csv
#    (or edit the path on line 7 of run_cytox_pred.py)
ls anticancer_unique.csv

# 4. run
python run_cytox_pred.py
```

### What it does, line by line

1. Reads `anticancer_unique.csv` (must contain a `smiles` column).
2. Validates each SMILES via RDKit (`Chem.MolFromSmiles`). Invalid SMILES are skipped — the `valid_smiles` column is `True`/`False`.
3. For each of the three cytotoxicity ensembles, runs `chemprop_predict` with:
   - `--features_generator rdkit_2d_normalized`
   - `--no_features_scaling`
4. Appends three new columns to the dataframe:
   - `cytotox_hepg2` — predicted probability of cytotoxicity against HepG2 (hepatocellular carcinoma)
   - `cytotox_hskmc` — predicted probability against human primary skeletal muscle cells (uses the `cytotox_primary` checkpoint folder)
   - `cytotox_imr90` — predicted probability against IMR-90 (lung fibroblasts)
5. Writes the result back to `anticancer_unique.csv` (overwrites in place).
6. Cleans up temporary files (`_temp_valid.csv`, `_pred_*.csv`).

### Reading the scores

Scores are probabilities in `[0, 1]`. Higher = more likely cytotoxic.

| Score | Interpretation |
|---|---|
| < 0.2 | Predicted **non-cytotoxic** to that cell line |
| 0.2 – 0.5 | Uncertain |
| > 0.5 | Predicted **cytotoxic** to that cell line |

Cutoffs follow the upstream paper's convention; calibrate against known actives/inactives in your own dataset before treating them as ground truth.

### Runtime

Roughly 1–3 minutes per ensemble for a few thousand compounds on a modern CPU, or ~30 seconds per ensemble on a single GPU. Three ensembles run sequentially, so total wall time is ~3–10 min per few-thousand-compound batch.

---

## Predicting against the other endpoints (antibiotic activity, β-lactam-removed, etc.)

`run_cytox_pred.py` hard-codes the three cytotoxicity ensembles. To run any other endpoint (e.g. `antibiotic_staph`), call Chemprop directly:

```bash
chemprop_predict \
  --test_path my_compounds.csv \
  --checkpoint_dir final_checkpoints/antibiotic_staph \
  --preds_path preds_antibiotic_staph.csv \
  --features_generator rdkit_2d_normalized \
  --no_features_scaling
```

The full list of endpoints is in `final_checkpoints/`. See `UPSTREAM_README.md` for the meaning of each.

---

## Troubleshooting

**`chemprop_predict: command not found`** — the `chemprop` conda env isn't activated. Run `conda activate chemprop`.

**`FileNotFoundError: anticancer_unique.csv`** — `run_cytox_pred.py` reads from the current working directory. `cd` into the repo before running.

**`KeyError: 'smiles'`** — your CSV's SMILES column has a different name. Either rename your column to `smiles` (lowercase) or edit line 15 of `run_cytox_pred.py`.

**`No such file or directory: final_checkpoints/cytotox_*`** — you skipped Setup step 3. Pull the checkpoints from upstream.

**RDKit warnings about valence / sanitization** — normal for messy input. Invalid SMILES are marked `valid_smiles=False` and skipped from prediction.

**Out of memory on GPU** — pass `--batch_size 50` (or smaller) inside the `cmd` string in `run_cytox_pred.py`.

---

## License

This repository inherits the [MIT License](LICENSE) of the upstream work © 2023 Felix Wong. Any additional files added in this fork (`run_cytox_pred.py`, `anticancer_unique.csv`, this `README.md`) are also released under MIT.

## Citation

If you use this in published work, cite the original paper:

> Wong, F. *et al.* Discovery of a structural class of antibiotics with explainable deep learning. *Nature* (2023). https://github.com/felixjwong/antibioticsai
