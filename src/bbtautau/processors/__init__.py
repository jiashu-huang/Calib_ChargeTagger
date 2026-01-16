from __future__ import annotations

import importlib
import sys

# Backward-compatibility shim for the moved processors package.
_ttSkimmer = importlib.import_module("processors.ttSkimmer")
_bbtautauSkimmer = importlib.import_module("processors.bbtautauSkimmer")
_GenSelection = importlib.import_module("processors.GenSelection")
_objects = importlib.import_module("processors.objects")

ttSkimmer = _ttSkimmer.ttSkimmer
bbtautauSkimmer = _bbtautauSkimmer.bbtautauSkimmer
GenSelection = _GenSelection
objects = _objects

sys.modules[__name__ + ".ttSkimmer"] = _ttSkimmer
sys.modules[__name__ + ".bbtautauSkimmer"] = _bbtautauSkimmer
sys.modules[__name__ + ".GenSelection"] = _GenSelection
sys.modules[__name__ + ".objects"] = _objects

__all__ = ["ttSkimmer", "bbtautauSkimmer", "GenSelection", "objects"]
