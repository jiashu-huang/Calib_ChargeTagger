# Logbook
Author: Jiashu Huang

## 2025-01-08
Worked through README.md all the way to
```bash
# Clone the repsitory as above if you haven't already
# Perform an editable installation
pip install -e .
# for committing to the repository
pip install pre-commit
pre-commit install
# Install as well the common HH utilities
cd boostedhh
pip install -e . # <- This is where it went wrong!
cd ..
```
Error message:
```text
(ttbar) [jhuan166@pbrux40cit Calib_ChargeTagger]$ cd boostedhh
(ttbar) [jhuan166@pbrux40cit boostedhh]$ pip install -e .
Obtaining file:///isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/boostedhh
ERROR: file:///isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/boostedhh does not appear to be a Python project: neither 'setup.py' nor 'pyproject.toml' found.
```

After trying to commit LOG.md:
```text
(ttbar) [jhuan166@pbrux40cit Calib_ChargeTagger]$ git add LOG.md
(ttbar) [jhuan166@pbrux40cit Calib_ChargeTagger]$ git commit -m "Add log"
[INFO] Initializing environment for https://github.com/psf/black-pre-commit-mirror.
[INFO] Initializing environment for https://github.com/psf/black-pre-commit-mirror:.[jupyter].
git [INFO] Initializing environment for https://github.com/adamchainz/blacken-docs.
[INFO] Initializing environment for https://github.com/adamchainz/blacken-docs:black==23.*.
[INFO] Initializing environment for https://github.com/pre-commit/pre-commit-hooks.
[WARNING] repo `https://github.com/pre-commit/pre-commit-hooks` uses deprecated stage names (commit, push) which will be removed in a future version.  Hint: often `pre-commit autoupdate --repo https://github.com/pre-commit/pre-commit-hooks` will fix this.  if it does not -- consider reporting an issue to that repo.
[INFO] Initializing environment for https://github.com/pre-commit/pygrep-hooks.
[INFO] Initializing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Initializing environment for https://github.com/shellcheck-py/shellcheck-py.
[INFO] Initializing environment for https://github.com/abravalheri/validate-pyproject.
[INFO] Initializing environment for https://github.com/abravalheri/validate-pyproject:.[all].
[INFO] Initializing environment for https://github.com/python-jsonschema/check-jsonschema.
[INFO] Installing environment for https://github.com/psf/black-pre-commit-mirror.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/adamchainz/blacken-docs.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/pre-commit/pre-commit-hooks.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/shellcheck-py/shellcheck-py.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/abravalheri/validate-pyproject.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/python-jsonschema/check-jsonschema.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
black-jupyter........................................(no files to check)Skipped
blacken-docs.............................................................Passed
check for added large files..............................................Passed
check for case conflicts.................................................Passed
check for merge conflicts................................................Passed
check for broken symlinks............................(no files to check)Skipped
check yaml...........................................(no files to check)Skipped
debug statements (python)............................(no files to check)Skipped
fix end of files.........................................................Failed
- hook id: end-of-file-fixer
- exit code: 1
- files were modified by this hook

Fixing LOG.md

mixed line ending........................................................Passed
python tests naming..................................(no files to check)Skipped
fix requirements.txt.................................(no files to check)Skipped
trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

Fixing LOG.md

rst ``code`` is two backticks........................(no files to check)Skipped
rst directives end with two colons...................(no files to check)Skipped
rst ``inline code`` next to normal text..............(no files to check)Skipped
ruff.................................................(no files to check)Skipped
shellcheck...........................................(no files to check)Skipped
Validate pyproject.toml..............................(no files to check)Skipped
Validate Dependabot Config (v2)......................(no files to check)Skipped
Validate GitHub Workflows............................(no files to check)Skipped
Validate ReadTheDocs Config..........................(no files to check)Skipped
```


## 2025-01-13

The following commands allowed me to install `boostedhh` successfully:

```bash
git submodule update --init --recursive
# optional sanity check
ls boostedhh

# install the submodule as a package
cd boostedhh
pip install -e .
cd ..
```

I need to update README.md later.

## 2025-01-14

To run `Calib_ChargeTagger`, ChatGPT Codex suggests:

```bash
micromamba activate ttbar
cd /home/jhuan166/Vcb/Calib_ChargeTagger
python src/run.py \
  --processor skimmer \
  --year 2022EE \
  --files /home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root \
  --files-name CHARGE \
  --file-tag charge_run1 \
  --save-root
```

Note that our dataset is `/TTtoLplusNu2Q-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22EEMiniAODv4-130X_mcRun3_2022_realistic_postEE_v6-v3/MINIAODSIM`,
so we must choose our tags accordingly.

Command line output:
```text
INFO:bbtautau.processors.ttSkimmer:Running skimmer with:
systematics False
region signal
Running on fileset {'2022EE_CHARGE': ['/home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root']}
Preprocessing 100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1/1 [ 0:00:00 < 0:00:00 | ? file/s ]
Processing   0% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0/4 [ 0:00:00 < -:--:-- | ? chunk/s ]INFO:root:# events 9295
/isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/boostedhh/src/boostedhh/corrections/jec_com
piled_py311.pkl.gz
starting object selection 2.71
Leptons 3.21
ak4 JECs 5.28
ak4 5.49
Processing   0% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0/4 [ 0:00:00 < -:--:-- | ? chunk/s ]INFO:root:Passing gen selection: 9295 / 9295
Processing   0% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0/4 [ 0:00:06 < -:--:-- | ? chunk/s ]
Traceback (most recent call last):
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 1654, in _work_function
    out = processor_instance.process(events)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/src/bbtautau/processors/ttSkimmer.py", line 443, in process
    eventVars["nBJets"] = ak.num(jets[jets.btagRobustParTAK4B >= bcut]).to_numpy()
                                                                 ^^^^
NameError: name 'bcut' is not defined

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/src/run.py", line 124, in <module>
    main(args)
  File "/isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/src/run.py", line 98, in main
    run_utils.run(
  File "/isilon/export/home/jhuan166/Vcb/Calib_ChargeTagger/boostedhh/src/boostedhh/run_utils.py", line 275, in run
    out, metrics = run(fileset, "Events", processor_instance=p)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 1700, in __call__
    wrapped_out = self.run(fileset, processor_instance, treename)
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 1848, in run
    wrapped_out, e = executor(chunks, closure, None)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 672, in __call__
    accumulate(
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/accumulator.py", line 95, in accumulate
    accum = next(gen)
            ^^^^^^^^^
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/accumulator.py", line 92, in <genexpr>
    gen = (x for x in items if x is not None)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/rich/progress.py", line 1231, in track
    for value in sequence:
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 1367, in automatic_retries
    raise e
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 1336, in automatic_retries
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/isilon/export/home/jhuan166/micromamba/envs/ttbar/lib/python3.11/site-packages/coffea/processor/executor.py", line 1656, in _work_function
    raise Exception(f"Failed processing file: {item!r}") from e
Exception: Failed processing file: WorkItem(dataset='2022EE_CHARGE', filename='/home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root', treename='Events', entrystart=0, entrystop=9295, fileuuid=b'd\x98\x02\x0e\xed\xf9\x11\xf0\xa5\xcf2\x80\x94\x80\xbe\xef', usermeta={})
```

Now try:
```bash
python src/run.py \
  --processor skimmer \
  --year 2022EE \
  --files /home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root \
  --files-name TTtoLplusNu2Q-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8 \
  --file-tag TTtoLplusNu2Q_2022EE \
  --save-root
```

Seems like the suggested patch is
```python
# Calib_ChargeTagger/src/bbtautau/processors/ttSkimmer.py:433
eventVars["nBJets"] = ak.num(
    jets[jets.btagRobustParTAK4B >= self.ak4_bjet_selection["bcut"]]
).to_numpy()
```

This works, so I am gonna push it up to GitHub.

## 2025-01-17

Now try:
```bash
python src/run.py \
  --processor skimmer \
  --year 2022EE \
  --files /home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root \
  --files-name TTtoLplusNu2Q-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8 \
  --file-tag TT1L2Q \
  --save-root
```

File is now saved at `/home/jhuan166/Vcb/Calib_ChargeTagger/nano_skim_TT1L2Q_batch_0.root`.

Turns out it is no different than the old file. Using `--file-tag TT1L2Q` is not working exactly as intended?

Try
```bash
python src/run.py \
  --processor skimmer \
  --year 2022EE \
  --files /home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root \
  --files-name TT1L2Q \
  --file-tag TT1L2Q \
  --save-root
```


## 2025-01-19

The command that works currently is
```bash
python src/run.py   --processor skimmer   --skimmer vcbSkimmer   --year 2022EE   --files /home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root   --files-name TT1L2Q   --file-tag TT1L2Q   --save-root
```
