# Calib_ChargeTagger (JH fork)

[Original repo](https://github.com/cramonal/Calib_ChargeTagger) created by Clara Ramon Alvarez.

## Overview

- Coffea-based NanoAOD skimming and object selection for bb->tautau/ttbar-style analyses.
- `src/run.py` runs the `ttSkimmer` processor, which reads NanoAOD ROOT files and writes new skim
  outputs (parquet and optional ROOT) without modifying input files in place.
- The `ttSkimmer` workflow (see `src/processors/ttSkimmer.py`) does the following:
  - Builds physics objects: tight electrons and muons; AK4 jets with JECs and lepton overlap removal.
  - Selects AK4 b-jets using `btagRobustParTAK4B` and a fixed working point (`bcut = 0.4319`).
  - Computes event-level quantities such as HT, jet/lepton multiplicities, and MET.
  - Saves trigger bits and trigger-matching flags (HLT selections are computed; triggers are not applied by
    default in the current configuration).
  - Applies event selections: MET filters, jet-veto map, >= 1 lepton, and >= 2 b-tagged AK4 jets
    (plus optional prescale when enabled).
  - For MC, adds weights and variations (pileup, PS, scale/PDF where applicable) and normalizes to xsec.
  - For TT1L2Q samples, saves gen-level/top-matching info for jets and leptons.
- Skimmed branch content includes lepton/jet kinematics and charge-tagger variables such as
  `ParTPosvsAll`, `ParTNegvsAll`, `ParTPosvsNeg`, `PflavCharge`, `FlavSplit`, and `btagRobustParTAK4B`,
  along with event IDs, pileup, HLT bits, and per-event weights.
- Gen-level masses saved by `GenSelection.py` (e.g., `GenTopMass`) come directly from the NanoAOD
  `GenPart.mass` branch (`GenPart_mass` in the input ROOT file), so they can vary event-by-event.
  b-quark masses are not saved by default; if needed, you can mirror the same pattern with
  `GenPart.mass` (noting some generators store b parton mass as 0) or replace with a fixed PDG mass.
- Supports local/dask execution and Condor submission via `src/condor/submit.py`.
- Postprocessing utilities for template production, sensitivity studies, BDT training, and combine workflows.
- Depends on the `boostedhh` utilities (submodule) for run orchestration and common corrections.

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
