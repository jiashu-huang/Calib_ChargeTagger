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
