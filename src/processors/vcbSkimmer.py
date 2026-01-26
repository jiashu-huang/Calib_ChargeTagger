"""
Skimmer for Vcb analysis, based on ttSkimmer.py.
Vcb analysis:
    p p > t t~, (t > b W, W > c b~), (t~ > b~ W~, W~ > l- nu~)

Author: Jiashu Huang (Brown U)

This is a Coffea processor that reads NanoAOD events, builds physics objects,
applies selections, computes weights, and writes a skimmed Parquet table.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from __future__ import annotations  # Allow forward references in type hints.

import logging  # Standard library logging for structured runtime messages.
import pathlib  # Path utilities used to build package-relative paths.
import time  # Simple wall-clock timing for debug prints.
from collections import OrderedDict  # Stable ordering for cutflow bookkeeping.

import awkward as ak  # Jagged-array operations for NanoAOD event data.
import numpy as np

# The following imports are from the boostedhh submodule.
from boostedhh import hh_vars  # Definitions for weight categories/normalization.
from boostedhh.processors import SkimmerABC, utils  # Base skimmer + common helpers.
from boostedhh.processors.corrections import (
    JECs,  # Jet energy corrections factory/loader.
    add_pileup_weight,  # Pileup reweighting for MC.
    add_ps_weight,  # Parton shower weights for MC variations.
    get_jetveto_event,  # Jet veto map selection per event.
    get_pdf_weights,  # PDF variation weights.
    get_scale_weights,  # Renormalization/factorization scale variations.
)
from boostedhh.processors.utils import (
    P4,  # Canonical 4-vector field mapping used in skim_vars.
    PAD_VAL,  # Padding sentinel value for missing entries.
    add_selection,  # Helper to register selections + update cutflow.
    pad_val,  # Helper to pad jagged arrays to fixed length.
)
from coffea import processor  # Coffea processor accumulator utilities.
from coffea.analysis_tools import PackedSelection, Weights  # Selection masks + weights.

from bbtautau.HLTs import HLTs  # Trigger lists grouped by year/region.

from . import GenSelection, objects  # Local gen selection and object definitions.

# -----------------------------------------------------------------------------
# End Imports
# -----------------------------------------------------------------------------

# mapping samples to the appropriate function for doing gen-level selections
gen_selection_dict = {
    "TT1L2Q": GenSelection.gen_selection_Vcb,
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

package_path = str(pathlib.Path(__file__).parent.parent.resolve())


# -----------------------------------------------------------------------------
# Class definition:
# -----------------------------------------------------------------------------


class vcbSkimmer(SkimmerABC):
    """
    Skims nanoaod files, saving selected branches and events passing preselection cuts
    (and triggers for data).
    """

    # skim_vars maps NanoAOD input fields to the specific output column names the skimmer will save.
    # Naming convention:
    #       "name in nano files": "name in the skimmed output"
    skim_vars = {  # noqa: RUF012
        "Jet": {
            **P4,
            "rawFactor": "rawFactor",
            "btagPNetB": "btagPNetB",  # RobustPrT and chargetagger
            "btagPNetCvB": "btagPNetCvB",
            "btagPNetCvL": "btagPNetCvL",
            "ParTPosvsAll": "ParTPosvsAll",
            "ParTNegvsAll": "ParTNegvsAll",
            "ParTPosvsNeg": "ParTPosvsNeg",
            "PflavCharge": "PflavCharge",
            "FlavSplit": "FlavSplit",
            # "btagRobustParTAK4B": "btagRobustParTAK4B",
        },
        "MET": {
            "pt": "Pt",
            "phi": "Phi",
        },
        "Lepton": {
            **P4,
            "charge": "charge",
        },
        "Event": {
            "run": "run",
            "event": "event",
            "luminosityBlock": "luminosityBlock",
        },
        "Pileup": {
            "nPU",
        },
        "TriggerObject": {
            "pt": "Pt",
            "eta": "Eta",
            "phi": "Phi",
            "filterBits": "Bit",
        },
        "HLT": {  # Save HLT through skim_vars?
            "Ele20_WPTight_Gsf": "Ele20_WPTight_Gsf",
        },
    }

    # We will not b-tag the jets at the Coffea skimmer processing level.
    # This is because our analysis would require testing multiple working points.

    # This is a small dict of lepton pT cuts when selecting b-jets for ak4 jets.
    ak4_jet_lepton_selection = {  # noqa: RUF012
        "electron_pt": 5,
        "muon_pt": 7,
    }

    # The constructor method, which is run automatically when an instance of the class is created.
    # Keep these variables in the function signature, as they are set by run.py.
    def __init__(
        self,
        xsecs: dict = None,
        save_systematics: bool = False,
        region: str = "signal",
        nano_version: str = "v12_private",
        fatjet_pt_cut: float = None,
        fatjet_bb_preselection: bool = False,
        prescale_factor: int = None,
    ):
        # Initialize the base Processor/Skimmer state first.
        super().__init__()

        # Store per-dataset cross sections (pb), falling back to empty if not provided.
        self.XSECS = xsecs if xsecs is not None else {}  # in pb

        # HLT selection
        # Build the HLT map, then pick the list for the requested analysis region.
        self.HLTs = {"signal": HLTs.hlt_list(hlt_prefix=False)}
        self.HLTs = self.HLTs[region]
        # Persist configuration flags for later processing steps.
        self._systematics = save_systematics
        self._nano_version = nano_version
        self._region = region
        # Coffea accumulator to collect outputs from process().
        self._accumulator = processor.dict_accumulator({})
        # Options controlling fatjet preselection and optional prescale.
        self._fatjet_bb_preselection = fatjet_bb_preselection
        self._prescale_factor = prescale_factor
        # Optional fatjet pT override.
        self._fatjet_pt_cut = fatjet_pt_cut

        # Log the configuration for user visibility.
        logger.info(
            f"Running skimmer with:\nsystematics {self._systematics}\nregion {self._region}"
        )

    @property  # a decorator that turns a method into a read-only attribute
    def accumulator(self):
        return self._accumulator  # This is defined above in __init__

    # The main processing method, called for each chunk of events.
    def process(self, events: ak.Array):
        """
        Runs event processor for different types of jets.

        Abbreviations:
        - JEC: Jet Energy Corrections
        - JMSR: Jet Mass Scale Resolution
        - ak4: anti-kT R=0.4 jets
        """

        # Define start time for debug prints
        start = time.time()

        # Log the number of input events.
        logging.info(f"# events {len(events)}")

        # Extract year and dataset from metadata.
        year = events.metadata["dataset"].split("_")[0]
        dataset = "_".join(events.metadata["dataset"].split("_")[1:])

        # isData is defined by the absence of genWeight.
        isData = not hasattr(events, "genWeight")

        # datasets for saving jec variations
        isJECs = (  # noqa: F841
            "HHto4B" in dataset
            or "TT" in dataset
            or "Wto2Q" in dataset
            or "Zto2Q" in dataset
            or "Hto2B" in dataset
            or "WW" in dataset
            or "ZZ" in dataset
            or "WZ" in dataset
        )

        # gen-weights
        gen_weights = events["genWeight"].to_numpy() if not isData else None
        n_events = len(events) if isData else np.sum(gen_weights)

        # selection and cutflow
        selection = PackedSelection()
        cutflow = OrderedDict()
        cutflow["all"] = n_events
        selection_args = (selection, cutflow, isData, gen_weights)

        # JEC factory loader
        JEC_loader = JECs(year)

        #########################
        # Object definitions
        #########################

        print("\nStarting object selection", f"{time.time() - start:.2f}")

        # Leptons (electrons and muons)
        num_leptons = 3  # We will save up to 3 leptons
        electrons, etrigvars = objects.good_electrons(events, events.Electron, year)
        muons, mtrigvars = objects.good_muons(events, events.Muon, year)

        # These are bools saying if the lepton is matched to a trigger object or not
        trigMatchVars = {**etrigvars, **mtrigvars}
        for key, val in trigMatchVars.items():
            trigMatchVars[key] = pad_val(val, num_leptons, False, axis=1).astype(int)

        print("* Leptons:\t", f"{time.time() - start:.2f}")

        # TODO: lepton systematics

        # AK4 Jets
        num_ak4_jets = 8
        jets, jec_shifted_jetvars = JEC_loader.get_jec_jets(
            events,
            events.Jet,
            year,
            isData,
            jecs=utils.jecs,
            fatjets=False,
            applyData=True,
            dataset=dataset,
            nano_version=self._nano_version,
        )

        if JEC_loader.met_factory is not None:
            met = JEC_loader.met_factory.build(events.PFMET, jets, {}) if isData else events.PFMET
        else:
            met = events.PFMET

        print("* ak4 JECs:\t", f"{time.time() - start:.2f}")

        jets = objects.good_ak4jets(
            jets,
            self._nano_version,
            events,
            muon_pt=self.ak4_jet_lepton_selection["muon_pt"],
            electron_pt=self.ak4_jet_lepton_selection["electron_pt"],
            dr_leptons=0.4,
        )
        ht = ak.sum(jets.pt, axis=1)
        print("* ak4:\t", f"{time.time() - start:.2f}")

        # We will not use ak8 jets or JMSR for this analysis.

        #########################
        # Save / derive variables
        #########################

        # Gen variables
        genVars = {}
        for d in gen_selection_dict:  # gen_selection_dict is defined in GenSelection.py
            if d in dataset:  # dataset is extracted from events metadata
                vars_dict = gen_selection_dict[d](
                    events, jets, electrons, muons, selection_args, P4
                )
                genVars = {**genVars, **vars_dict}

        # used for normalization to cross section below
        gen_selected = (
            selection.all(*selection.names)
            if len(selection.names)
            else np.ones(len(events)).astype(bool)
        )
        logging.info(f"Passing gen selection: {np.sum(gen_selected)} / {len(events)}")

        # Lepton variables
        electronVars = {
            f"Electron{key}": pad_val(electrons[var], num_leptons, axis=1)
            for (var, key) in self.skim_vars["Lepton"].items()
        }
        muonVars = {
            f"Muon{key}": pad_val(muons[var], num_leptons, axis=1)
            for (var, key) in self.skim_vars["Lepton"].items()
        }
        leptonVars = {**electronVars, **muonVars}

        # AK4 Jet variables
        jet_skimvars = self.skim_vars["Jet"]
        if not isData:
            jet_skimvars = {
                **jet_skimvars,
                "pt_gen": "MatchedGenJetPt",
            }

        ak4JetVars = {
            f"ak4Jet{key}": pad_val(jets[var], num_ak4_jets, axis=1)
            for (var, key) in jet_skimvars.items()
        }
        # ak4bTagJetVars = {
        #     f"ak4bTagJet{key}": pad_val(ak4_bjets[var], 6, axis=1)
        #     for (var, key) in jet_skimvars.items()
        # }

        """
        if len(ak4_jets_awayfromak8) == 2:
            ak4JetAwayVars = {
                f"AK4JetAway{key}": pad_val(
                    ak.concatenate(
                        [ak4_jets_awayfromak8[0][var], ak4_jets_awayfromak8[1][var]], axis=1
                    ),
                    2,
                    axis=1,
                )
                for (var, key) in jet_skimvars.items()
            }
        else:
            ak4JetAwayVars = {
                f"AK4JetAway{key}": pad_val(ak4_jets_awayfromak8[var], 2, axis=1)
                for (var, key) in jet_skimvars.items()
            }
        """
        # MET
        metVars = {f"MET{key}": met[var].to_numpy() for (var, key) in self.skim_vars["MET"].items()}

        # Event variables
        eventVars = {
            key: events[val].to_numpy()
            for key, val in self.skim_vars["Event"].items()
            if key in events.fields
        }
        eventVars["ht"] = ht.to_numpy()
        eventVars["nElectrons"] = ak.num(electrons).to_numpy()
        eventVars["nMuons"] = ak.num(muons).to_numpy()
        eventVars["nJets"] = ak.num(jets).to_numpy()
        # eventVars["nBJets"] = ak.num(
        #     jets[jets.btagRobustParTAK4B >= self.ak4_bjet_selection["bcut"]]
        # ).to_numpy()

        # jin for CA
        # eventVars["CA_matched_tau_pt_sum"] = ca_tau_pt_sum.to_numpy()
        # eventVars["CA_tau_idx_0"] = ca_tau_indices[:, 0].to_numpy()
        # eventVars["CA_tau_idx_1"] = ca_tau_indices[:, 1].to_numpy()
        # eventVars["CA_best_fatjet_idx"] = ca_best_fatjet_idx.to_numpy()

        if isData:
            pileupVars = {key: np.ones(len(events)) * PAD_VAL for key in self.skim_vars["Pileup"]}
        else:
            pileupVars = {key: events.Pileup[key].to_numpy() for key in self.skim_vars["Pileup"]}
        pileupVars = {**pileupVars, "nPV": events.PV["npvs"].to_numpy()}

        # Trigger variables
        HLTVars = {}
        zeros = np.zeros(len(events), dtype="int")
        for trigger in self.HLTs[year]:
            if trigger in events.HLT.fields:
                HLTVars[f"HLT_{trigger}"] = events.HLT[trigger].to_numpy().astype(int)
            else:
                logger.warning(f"Missing {trigger}!")
                HLTVars[f"HLT_{trigger}"] = zeros

        print("HLT vars", f"{time.time() - start:.2f}")

        # # JEC variations for VBF Jets
        # if self._region == "signal" and isJECs:
        #     for var in ["pt"]:
        #         key = self.skim_vars["Jet"][var]
        #         for label, shift in utils.jecs.items():
        #             if shift in ak.fields(vbf_jets):
        #                 for vari in ["up", "down"]:
        #                     vbfJetVars[f"VBFJet{key}_{label}_{vari}"] = pad_val(
        #                         vbf_jets[shift][vari][var], 2, axis=1
        #                     )

        skimmed_events = {
            **genVars,
            **eventVars,
            **pileupVars,
            **trigMatchVars,
            **HLTVars,
            **leptonVars,
            **ak4JetVars,
            # **ak4bTagJetVars,
            **metVars,
            # **bbFatJetVars,
            # **trigObjFatJetVars,
        }

        # if self._region == "signal":
        #     bdtVars = self.getBDT(bbFatJetVars, vbfJetVars, ak4JetAwayVars, met_pt, "")
        #     print(bdtVars)
        #     skimmed_events = {
        #         **skimmed_events,
        #         **bdtVars,
        #     }

        print("Vars", f"{time.time() - start:.2f}")

        ######################
        # Selection
        ######################

        HLT_triggered = np.any(
            np.array(
                [events.HLT[trigger] for trigger in self.HLTs[year] if trigger in events.HLT.fields]
            ),
            axis=0,
        )

        # don't apply triggers for now, for trigger studies etc.
        apply_trigger = False
        if apply_trigger:
            add_selection("trigger", HLT_triggered, *selection_args)

        # metfilters
        cut_metfilters = np.ones(len(events), dtype="bool")
        for mf in utils.met_filters:
            if mf in events.Flag.fields:
                cut_metfilters = cut_metfilters & events.Flag[mf]
        add_selection("met_filters", cut_metfilters, *selection_args)

        # jet veto maps
        cut_jetveto = get_jetveto_event(jets, year)
        add_selection("ak4_jetveto", cut_jetveto, *selection_args)

        # # >=2 AK8 jets passing selections
        # add_selection("ak8_numjets", (ak.num(fatjets) >= 2), *selection_args)
        add_selection("1lep", ak.num(muons) + ak.num(electrons) >= 1, *selection_args)
        # add_selection("2bjets", ak.num(ak4_bjets) >= 2, *selection_args)
        # >=1 AK8 jets with pT cut (230 GeV by default)

        # # >=1 AK8 jets with mSD >= 40 GeV
        # cut_mass = np.sum(ak8FatJetVars["ak8FatJetMsd"] >= 40, axis=1) >= 1
        # add_selection("ak8_mass", cut_mass, *selection_args)

        # Veto leptons
        # add_selection(
        #     "0lep",
        #     (ak.sum(veto_muon_sel, axis=1) == 0) & (ak.sum(veto_electron_sel, axis=1) == 0),
        #     *selection_args,
        # )

        # if self._region == "signal":
        #     # >=1 bb AK8 jets (ordered by TXbb) with TXbb > 0.8
        #     cut_txbb = (
        #         np.sum(
        #             bbFatJetVars[f"bbFatJet{txbb_str}"] >= self.preselection[self.txbb],
        #             axis=1,
        #         )
        #         >= 1
        #     )
        #     add_selection("ak8bb_txbb0", cut_txbb, *selection_args)

        # VBF veto cut (not now)
        # add_selection("vbf_veto", ~(cut_vbf), *selection_args)
        """
        if self._fatjet_bb_preselection:
            # at least 1 jet with ParTXbbvsQCDTop > 0.3
            cut_bb = (
                np.sum(
                    ak8FatJetVars["ak8FatJetParTXbbvsQCDTop"] >= self.preselection["glopart-v2"],
                    axis=1,
                )
                >= 1
            )
            add_selection("ak8_bb_preselection", cut_bb, *selection_args)
        """
        if self._prescale_factor:
            cut_prescale = events.event % self._prescale_factor == 0
            add_selection("prescale", cut_prescale, *selection_args)

        print("Selection", f"{time.time() - start:.2f}")

        # -----------------------------------------------------------------------------
        # Event Weights (per-event)
        # -----------------------------------------------------------------------------
        # Data events: weight = 1. MC events: genweight * corrections * normalization.
        totals_dict = {"nevents": n_events}  # Track totals for reporting/normalization.

        if isData:
            # Data has no MC corrections; assign unit weight per event.
            skimmed_events["weight"] = np.ones(n_events)
        else:
            # MC: compute nominal + systematic weights inside add_weights(...).
            weights_dict, totals_temp = self.add_weights(
                events,
                year,
                dataset,
                gen_weights,
                gen_selected,
            )
            # Merge the weight columns into the skim output and keep the totals metadata.
            skimmed_events = {**skimmed_events, **weights_dict}
            totals_dict = {**totals_dict, **totals_temp}

        ##############################
        # Reshape and apply selections
        ##############################

        # This is where the selection happens!
        sel_all = selection.all(*selection.names)
        skimmed_events = {
            key: value.reshape(len(skimmed_events["weight"]), -1)[sel_all]
            for (key, value) in skimmed_events.items()
        }

        dataframe = self.to_pandas(skimmed_events)
        fname = events.behavior["__events_factory__"]._partition_key.replace("/", "_") + ".parquet"
        self.dump_table(dataframe, fname)

        logger.info(f"Cutflow:\n{cutflow}")

        print("Return ", f"{time.time() - start:.2f}")
        print("Columns:", print(list(dataframe.columns)))
        return {year: {dataset: {"totals": totals_dict, "cutflow": cutflow}}}

    def postprocess(self, accumulator):
        return accumulator

    def add_weights(
        self,
        events,
        year,
        dataset,
        gen_weights,
        gen_selected,
    ) -> tuple[dict, dict]:
        """
        Adds weights and variations, saves totals for all norm preserving weights and variations
        """

        # -------------------------------------------------------------------------
        # Per-event weight construction (MC only)
        # -------------------------------------------------------------------------
        # 1) Create a Coffea Weights container that can combine multiple factors.
        weights = Weights(len(events), storeIndividual=True)

        # 2) Seed the event weight with the generator weight from NanoAOD.
        weights.add("genweight", gen_weights)

        # 3) Add standard MC corrections/variations.
        add_pileup_weight(weights, year, events.Pileup.nPU.to_numpy(), dataset)
        add_ps_weight(weights, events.PSWeight)

        logger.debug("weights", extra=weights._weights.keys())

        ###################### Save all the weights and variations ######################

        # 4) Identify weights that should preserve normalization across variations.
        norm_preserving_weights = hh_vars.norm_preserving_weights

        # 5) Prepare output dictionaries.
        weights_dict = {}
        totals_dict = {}

        # 6) Compute the nominal per-event combined weight.
        weights_dict["weight"] = weights.weight()

        # 7) Also compute the normalization-preserving partial weight and its total.
        weight_np = weights.partial_weight(include=norm_preserving_weights)
        totals_dict["np_nominal"] = np.sum(weight_np[gen_selected])

        # 8) If requested, compute per-event systematic variations.
        if self._systematics:
            for systematic in list(weights.variations):
                weights_dict[f"weight_{systematic}"] = weights.weight(modifier=systematic)

                if utils.remove_variation_suffix(systematic) in norm_preserving_weights:
                    var_weight = weights.partial_weight(include=norm_preserving_weights)
                    # modify manually
                    if "Down" in systematic and systematic not in weights._modifiers:
                        var_weight = (
                            var_weight / weights._modifiers[systematic.replace("Down", "Up")]
                        )
                    else:
                        var_weight = var_weight * weights._modifiers[systematic]

                    # need to save total # events for each variation for normalization in post-processing
                    totals_dict[f"np_{systematic}"] = np.sum(var_weight[gen_selected])

        # 9) Debugging aid: store each individual weight factor separately.
        for key in weights._weights:
            weights_dict[f"single_weight_{key}"] = weights.partial_weight([key])

        # 10) Add theory variations (scale/PDF) for supported datasets.
        ###################### alpha_S and PDF variations ######################

        if ("HHTobbbb" in dataset or "HHto4B" in dataset) or dataset.startswith("TTTo"):
            scale_weights = get_scale_weights(events)
            if scale_weights is not None:
                weights_dict["scale_weights"] = (
                    scale_weights * weights_dict["weight"][:, np.newaxis]
                )
                totals_dict["np_scale_weights"] = np.sum(
                    (scale_weights * weight_np[:, np.newaxis])[gen_selected], axis=0
                )

        if "HHTobbbb" in dataset or "HHto4B" in dataset:
            pdf_weights = get_pdf_weights(events)
            weights_dict["pdf_weights"] = pdf_weights * weights_dict["weight"][:, np.newaxis]
            totals_dict["np_pdf_weights"] = np.sum(
                (pdf_weights * weight_np[:, np.newaxis])[gen_selected], axis=0
            )

        # 11) Apply cross section * luminosity normalization to all weights.
        ###################### Normalization (Step 1) ######################

        weight_norm = self.get_dataset_norm(year, dataset)
        # normalize all the weights to xsec, needs to be divided by totals in Step 2 in post-processing
        for key, val in weights_dict.items():
            weights_dict[key] = val * weight_norm

        # 12) Also store the unnormalized nominal weight for post-processing checks.
        weights_dict["weight_noxsec"] = weights.weight()

        return weights_dict, totals_dict
