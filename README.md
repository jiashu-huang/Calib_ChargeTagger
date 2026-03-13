# Calib_ChargeTagger (JH fork)

[Original repo](https://github.com/cramonal/Calib_ChargeTagger) created by Clara Ramon Alvarez.

## Overview

- Coffea-based NanoAOD skimming for the Vcb charge-tagger calibration, studying
  **pp -> tt, (t -> bW, W -> cb), (t -> bW, W -> l nu)**.
- `src/run.py` runs a skimmer processor (`vcbSkimmer` or `ttSkimmer`) that reads NanoAOD ROOT files
  and writes skimmed outputs (parquet and optional ROOT) without modifying input files in place.
- The `vcbSkimmer` workflow (see `src/processors/vcbSkimmer.py`) does the following:
  - Builds physics objects: tight electrons (mvaIso WP90) and muons (tightId, pfRelIso04 < 0.15);
    AK4 jets with JECs and lepton overlap removal against the prompt, trigger-matched lepton only.
  - Computes event-level quantities: HT, jet/lepton multiplicities (`nJets`, `nElectrons`, `nMuons`),
    MET (pt and phi), pileup (`nPU`, `nPV`).
  - Requires single-lepton triggers (`HLT_IsoMu24` or `HLT_Ele32_WPTight_Gsf`). Events failing
    both are discarded.
  - Applies event selections: single-lepton trigger, MET filters, jet-veto map, >= 1 lepton.
  - For MC, adds weights (genweight, pileup, ISR/FSR parton shower) normalized to cross-section,
    plus `finalWeight = weight / np_nominal`.
  - For TT1L2Q samples, saves generator-level top/W/quark kinematics and reco-to-gen
    truth-matching (see below).
- Supports local/dask execution and Condor submission via `src/condor/submit.py`.
- Depends on the `boostedhh` utilities (submodule) for run orchestration and common corrections.

### Output branch summary (vcbSkimmer)

The skimmed ROOT file contains an `Events` tree. Branches are organized as follows
(see `tests/outfile/test-output-schema.csv` for the full list):

| Category | Branches | Type | Count |
|----------|----------|------|-------|
| **Electrons** | `ElectronPt/Eta/Phi/Mass`, `Electroncharge`, `ElectronTrigMatchEGamma` | Double_t / Long64_t | x3 objects |
| **Muons** | `MuonPt/Eta/Phi/Mass`, `Muoncharge`, `MuonTrigMatchMuon` | Double_t / Long64_t | x3 objects |
| **AK4 jets** | `ak4JetPt/Eta/Phi/Mass`, `ak4JetrawFactor`, `ak4JetMatchedGenJetPt` | Double_t | x8 objects |
| **Jet b-tagging** | `ak4JetbtagPNetB`, `ak4JetbtagPNetCvB`, `ak4JetbtagPNetCvL` | Double_t | x8 objects |
| **Charge tagger** | `ak4JetParTPosvsAll`, `ak4JetParTNegvsAll`, `ak4JetParTPosvsNeg`, `ak4JetPflavCharge` | Double_t / Long64_t | x8 objects |
| **Jet flavor** | `ak4JetFlavSplit` | Long64_t | x8 objects |
| **Top matching** | `ak4NumBMatchedTop1/2`, `ak4NumQMatchedTop1/2` (jets); `electronsNumlMatchedTop1`, `muonsNumlMatchedTop1` (leptons) | Long64_t | x6 jets, x3 leptons |
| **Gen-level tops** | `GenTopPt/Eta/Phi/Mass` (x2 tops), `GenTopW0/W1 Pt/Eta/Phi/Mass`, `GenTopB0/B1 Pt/Eta/Phi/Mass` | Float_t | per event |
| **Gen-level quarks** | `GenQ1/Q2 Pt/Eta/Phi/Mass/PdgId`, `GenWbPt/Eta/Phi/Mass`, `GenWtoBC` | Float_t / Int_t / Bool_t | per event |
| **HLT triggers** | `HLT_IsoMu24`, `HLT_Ele32_WPTight_Gsf`, and 5 cross/dilepton triggers | Long64_t | per event |
| **MET** | `METPt`, `METPhi` | Float_t | per event |
| **Event IDs** | `run`, `event`, `luminosityBlock` | UInt_t / ULong64_t | per event |
| **Event counts** | `ht`, `nJets`, `nElectrons`, `nMuons`, `nPU`, `nPV` | Float_t / Long64_t / Int_t / UChar_t | per event |
| **Weights** | `weight`, `weight_noxsec`, `finalWeight`, `single_weight_genweight/pileup/ISRPartonShower/FSRPartonShower` | Double_t | per event |

Unused object slots are padded with `-99999`.

### TT1L2Q-specific gen-level branches

Gen-level branches are only computed when the dataset name matches a key in `gen_selection_dict`
(currently `TT1L2Q` or `TTtoLNu2Q`). The function `GenSelection.gen_selection_Vcb` extracts
generator-truth information from NanoAOD `GenPart` for the semi-leptonic ttbar topology.

**Gen-level kinematics:**

| Branches | Physics |
|----------|---------|
| `GenTopPt/Eta/Phi/Mass` (x2) | The two hard-process top quarks (t and t-bar). |
| `GenTopW0/W1 Pt/Eta/Phi/Mass` | W bosons from each top decay. |
| `GenTopB0/B1 Pt/Eta/Phi/Mass` | b-quarks from each top decay (t -> bW). |
| `GenQ1/Q2 Pt/Eta/Phi/Mass` | Quark daughters from the hadronic W decay (e.g. W -> cs or W -> ud). |
| `GenQ1PdgId`, `GenQ2PdgId` | PDG IDs of those quarks (1=d, 2=u, 3=s, 4=c, 5=b; negative = antiquark). |
| `GenWbPt/Eta/Phi/Mass` | The b-quark from W -> bc, if present. Padded to -99999 otherwise. |
| `GenWtoBC` | Boolean flag: True if any W in the event decayed to both a b and a c quark (the rare signal decay). |

**Reco-to-gen truth matching** (computed via dR cone matching):

| Branches | Cone | Physics |
|----------|------|---------|
| `ak4NumBMatchedTop1` (x6 jets) | dR < 0.4 | 1 if the reco jet is matched to the b-quark from the first top. |
| `ak4NumBMatchedTop2` (x6 jets) | dR < 0.4 | 1 if matched to the b-quark from the second top. |
| `ak4NumQMatchedTop1` (x6 jets) | dR < 0.4 | 1 if matched to the first quark from the hadronic W (GenQ1). |
| `ak4NumQMatchedTop2` (x6 jets) | dR < 0.4 | 1 if matched to the second quark from the hadronic W (GenQ2). |
| `electronsNumlMatchedTop1` (x3) | dR < 0.2 | 1 if the reco electron is matched to the gen lepton from the leptonic W. |
| `muonsNumlMatchedTop1` (x3) | dR < 0.2 | 1 if the reco muon is matched to the gen lepton from the leptonic W. |

These matching flags enable studies of reconstruction efficiency, jet assignment accuracy,
and charge-tagger calibration by comparing reco-level b/c-jet discrimination against gen-truth.

## Setting up package

### Creating a virtual environment

First, create a virtual environment (`micromamba` is recommended):

```bash
# Clone the repository
git clone --recursive https://github.com/cramonal/Calib_ChargeTagger.git
cd Calib_ChargeTagger
# Download the micromamba setup script (change if needed for your machine https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
# Install: (the micromamba directory can end up taking O(1-10GB) so make sure the directory you're using allows that quota)
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
# Alternative (Homebrew-based) installer if the above times out:
# ./setup_micromamba.sh
# You may need to restart your shell
micromamba env create -f environment.yaml
micromamba activate ttbar
```

### Installing package

**Remember to install this in your mamba environment**.

```bash
# Clone the repsitory as above if you haven't already
# Perform an editable installation
pip install -e .
# for committing to the repository
pip install pre-commit
pre-commit install
# Install as well the common HH utilities
cd boostedhh
pip install -e .
cd ..
```

### Troubleshooting

- If your default `python` in your environment is not Python 3, make sure to use
  `pip3` and `python3` commands instead.

- You may also need to upgrade `pip` to perform the editable installation:

```bash
python3 -m pip install -e .
```

## Running coffea processors

### Setup

For submitting to condor, all you need is python >= 3.7.

For running locally, follow the same virtual environment setup instructions
above and activate the environment.

```bash
micromamba activate ttbar
```

Clone the repository:

```
git clone --recursive https://github.com/cramonal/Calib_ChargeTagger.git
pip install -e .
```

### Running locally

For testing, e.g.:

```bash
python src/run.py --samples TT --subsamples TTto4Q --starti 0 --endi 1 --year 2022 --processor skimmer
```

#### Vcb skim from local files

When running the vcbSkimmer on local ROOT files (e.g. CMSSW NanoAOD output), use `--files`
with `--files-name TT1L2Q` so that the dataset name matches the `gen_selection_dict` in
`vcbSkimmer.py` — otherwise generator-level branches (`GenQ1/GenQ2`, `GenTopB`, `GenWtoBC`)
will **not** be computed.

Use `--batch-size 9999` to produce a single merged output ROOT file instead of many batches,
and `--write-final-weight` to include the properly normalized `finalWeight` branch:

```bash
python src/run.py \
  --processor skimmer \
  --skimmer vcbSkimmer \
  --year 2022 \
  --files /path/to/input1.root /path/to/input2.root ... \
  --files-name TT1L2Q \
  --save-root \
  --write-final-weight \
  --chunksize 100000 \
  --maxchunks 0 \
  --batch-size 9999
```

Key flags:
- **`--files-name TT1L2Q`**: Required for gen-level quark/b branches. Must match a key in `gen_selection_dict`.
- **`--write-final-weight`**: Adds the `finalWeight` branch (xsec-normalized).
- **`--batch-size 9999`**: Merges all output chunks into one file (`nano_skim_TT1L2Q_batch_0.root`).
- **`--maxchunks 0`**: Process all events (no limit).

### Condor jobs


Or from a YAML:

```bash
python src/condor/submit.py --yaml src/condor/submit_configs/25Apr5All.yaml --analysis bbtautau --git-branch yourbranch --site lpc --save-sites ucsd lpc --processor skimmer --tag 25Apr5AddVars --year 2022 [--submit]
```

### Checking jobs

e.g.


```bash
python boostedhh/condor/check_jobs.py --analysis bbtautau --tag 25Apr24_v12_private_signal --processor skimmer --check-running --year 2022EE
```

## Testing after code changes

After modifying `vcbSkimmer.py` or its dependencies, run the integration test to confirm
the output file structure is correct:

```bash
micromamba run -n ttbar python tests/test_run.py \
  /home/jhuan166/Vcb/cmssw-output/TTtoLplusNu2Q-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8__Run3Summer22MiniAODv4-130X_mcRun3_2022_realistic_v5-v1__MINIAODSIM/batch_000/2b148b77-ce18-4dde-998a-c5ba8c7ab2d5_CMSSW_15_CHARGE_NanoAOD.root
```

Three files are written to `tests/outfile/`:

- **`test-output.root`** — skimmed ROOT file (tree: `Events`) produced by `vcbSkimmer`.
- **`test-output-0th-event.txt`** — human-readable dump of the 0th event, one line per branch:
  ```
  Tree: Events
  Entry: 0
  GenQ1Eta (Float_t) = 0.6640625
  GenQ1PdgId (Int_t) = 1
  ...
  ```
- **`test-output-schema.csv`** — two-column CSV listing every branch name and its ROOT type:
  ```
  variable_name,variable_type
  GenQ1Eta,Float_t
  GenQ1PdgId,Int_t
  ...
  ```

Use the schema CSV to quickly check whether expected branches are present and have the
correct types after a change.

## Primary analysis ROOT file (lep-overlap branch)

Use the following file as the correctly processed primary-analysis output:

`/home/jhuan166/Vcb/Calib_ChargeTagger/nano_skim_all_merged_000_024_lep-overlap_uptodate_20260304_lz4.root`

Notes:
- This merged file covers files `000` to `024`.
- It comprises about 10% of all input events.
- For full-dataset normalization, each event basically has an effective `10x` weight.
