"""
Runs coffea processors on the LPC via either condor or dask.

Author: Jiashu Huang
Date: Jan 2025

Usage:
python src/run.py \
  --processor skimmer \
  --skimmer vcbSkimmer \
  --year 2022 \
  --files /home/jhuan166/Vcb/CMSSW_15_1_0_patch4/output/315d7993-98ba-431b-8fb5-8835abca47cb_CMSSW_15_CHARGE_NanoAOD.root \
  --files-name TT1L2Q \
  --file-tag TT1L2Q \
  --save-root \
  --chunksize 40000 \
  --maxchunks 0
"""

from __future__ import annotations

import argparse
import importlib
import inspect
from pathlib import Path

import yaml
from boostedhh import run_utils
from boostedhh.hh_vars import DATA_SAMPLES
from boostedhh.processors import SkimmerABC
from boostedhh.xsecs import xsecs

from bbtautau import bbtautau_utils


def _parse_skimmer_arg(skimmer: str | None) -> tuple[str, str | None]:
    """
    Docstring for _parse_skimmer_arg

    :param skimmer: Description
    :type skimmer: str | None
    :return: Description
    :rtype: tuple[str, str | None]

    Resolve the "--skimmer" value into a module name and optional class name.
    Examples:
        "ttSkimmer" -> ("ttSkimmer", None)
        "vcbSkimmer.py" -> ("vcbSkimmer", None)
    """
    if not skimmer:
        return "ttSkimmer", None

    class_name = None
    module_part = skimmer

    raw_name = Path(module_part).name
    if raw_name.endswith(".py"):
        raw_name = raw_name[:-3]
    module_name = raw_name.split(".")[-1]

    return module_name, class_name


def _select_skimmer_class(
    skimmer_module, module_name: str, class_name: str | None
) -> type[SkimmerABC]:
    # Given an imported module and an optional class name, find the SkimmerABC subclass.
    # Priority: explicit class name -> class matching module name -> unique subclass in module.

    # If a class name is given, try to get it directly.
    if class_name:
        try:
            return getattr(skimmer_module, class_name)
        except AttributeError as exc:
            raise ValueError(
                f"Skimmer class {class_name} not found in processors.{module_name}"
            ) from exc

    if hasattr(skimmer_module, module_name):
        return getattr(skimmer_module, module_name)

    candidates = []
    for _, obj in vars(skimmer_module).items():
        if (
            inspect.isclass(obj)
            and issubclass(obj, SkimmerABC)
            and obj is not SkimmerABC
            and obj.__module__ == skimmer_module.__name__
        ):
            candidates.append(obj)

    # If the module defines exactly one SkimmerABC subclass, pick it.
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        options = ", ".join(sorted(cls.__name__ for cls in candidates))
        raise ValueError(
            "Multiple skimmer classes found in processors."
            f"{module_name}: {options}. Use --skimmer module:Class to select one."
        )

    raise ValueError(f"No SkimmerABC subclass found in processors.{module_name}")


def get_processor(
    processor: str,
    save_systematics: bool | None = None,
    region: str | None = None,
    nano_version: str | None = None,
    fatjet_pt_cut: float | None = None,
    fatjet_bb_preselection: bool | None = None,
    prescale_factor: int | None = None,
    skimmer: str | None = None,
):
    # Factory for processor instances. Currently only "skimmer" is supported.
    # This means that your input needs to have "--processor skimmer" in order to run.
    if processor == "skimmer":
        # Resolve module + class, then import and select the skimmer class.
        skimmer_name, class_name = _parse_skimmer_arg(skimmer)
        skimmer_module = importlib.import_module(f"processors.{skimmer_name}")
        skimmer_cls = _select_skimmer_class(skimmer_module, skimmer_name, class_name)

        # Instantiate the skimmer and pass runtime configuration.
        return skimmer_cls(
            xsecs=xsecs,
            save_systematics=save_systematics,
            region=region,
            nano_version=nano_version,
            fatjet_pt_cut=fatjet_pt_cut,
            fatjet_bb_preselection=fatjet_bb_preselection,
            prescale_factor=prescale_factor,
        )


def main(args):
    # Build the processor with all CLI-configured options.
    p = get_processor(
        args.processor,
        args.save_systematics,
        args.region,
        args.nano_version,
        args.fatjet_pt_cut,
        args.fatjet_bb_preselection,
        args.prescale_factor,
        args.skimmer,
    )

    # Select output formats by processor type (skimmer always saves both).
    save_parquet = {"skimmer": True}[args.processor]
    save_root = {"skimmer": True}[args.processor]

    # By default, skip bad files unless we are explicitly running on data.
    skipbadfiles = True

    if len(args.files):
        # Direct file list given on the command line: build a single-entry fileset.
        fileset = {f"{args.year}_{args.files_name}": args.files}
        skipbadfiles = False  # not added functionality for args.files yet
    else:
        if args.yaml:
            # YAML workflow: load list of samples + subsamples for the given year.
            with Path(args.yaml).open() as file:
                samples_to_submit = yaml.safe_load(file)
            try:
                samples_to_submit = samples_to_submit[args.year]
            except Exception as e:
                raise KeyError(f"Year {args.year} not present in yaml dictionary") from e

            samples = samples_to_submit.keys()
            subsamples = []
            for sample in samples:
                subsamples.extend(samples_to_submit[sample].get("subsamples", []))
        else:
            # CLI workflow: use samples + subsamples provided in arguments.
            samples = args.samples
            subsamples = args.subsamples

        # Build fileset from index JSON with start/end slice limits.
        fileset = run_utils.get_fileset(
            f"data/index_{args.year}.json",
            args.year,
            samples,
            subsamples,
            args.starti,
            args.endi,
        )

        # don't skip "bad" files for data - we want it throw an error in that case
        for key in fileset:
            if key in DATA_SAMPLES:
                skipbadfiles = False

    print(f"Running on fileset {fileset}")
    if args.executor == "dask":
        # Distributed execution on a Dask cluster.
        run_utils.run_dask(p, fileset, args)
    else:
        # Local execution via Coffea's iterative executor.
        run_utils.run(
            p,
            fileset,
            chunksize=args.chunksize,
            maxchunks=args.maxchunks,
            skipbadfiles=skipbadfiles,
            save_parquet=save_parquet,
            save_root=save_root and args.save_root,
            filetag=f"{args.starti}-{args.endi}" if args.file_tag is None else args.file_tag,
            batch_size=args.batch_size,
        )


if __name__ == "__main__":
    # Top-level CLI entrypoint: define arguments, validate, then launch main().
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # Common args shared across different workflows.
    run_utils.parse_common_run_args(parser)
    run_utils.parse_common_hh_args(parser)
    bbtautau_utils.parse_common_run_args(parser)
    parser.add_argument(
        "--skimmer",
        type=str,
        default="ttSkimmer",
        help=(
            "Skimmer module name in src/processors, optionally with class name "
            "(e.g., ttSkimmer, vcbSkimmer.py, vcbSkimmer:ttSkimmer)."
        ),
    )
    args = parser.parse_args()

    # Normalize "year" argument to a single value if a one-element list is passed.
    if isinstance(args.year, list):
        if len(args.year) == 1:
            args.year = args.year[0]
        else:
            raise ValueError("Running on multiple years is not supported yet")

    main(args)
