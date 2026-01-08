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
