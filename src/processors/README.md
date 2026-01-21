# Processors

This folder contains the skimmers used by `Calib_ChargeTagger` analyses.
You should input your skimmer's name as an argument for `--skimmer` of [src/run.py](../run.py), e.g. `... --skimmer vcbSkimmer.py ...`.

When you write your skimmer, make sure you add the generator-info processing function in `GenSelection.py`.
