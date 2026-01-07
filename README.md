# Calib_ChargeTagger (JH fork)
[Original repo](https://github.com/cramonal/Calib_ChargeTagger) created by Clara Ramon Alvarez. 

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


