"""
Skimmer for Vcb analysis.

Author: Jiashu Huang (Brown U)
"""

from __future__ import annotations

import logging
import pathlib
import time
from collections import OrderedDict

import awkward as ak
import numpy as np
from boostedhh import hh_vars
from boostedhh.processors import SkimmerABC, utils
from boostedhh.processors.corrections import (
    JECs,
    add_pileup_weight,
    add_ps_weight,
    get_jetveto_event,
    get_pdf_weights,
    get_scale_weights,
)
from boostedhh.processors.utils import (
    P4,
    PAD_VAL,
    add_selection,
    pad_val,
)
from coffea import processor
from coffea.analysis_tools import PackedSelection, Weights

from bbtautau.HLTs import HLTs

from . import GenSelection, objects

# ------------------------------------------------------------------------------
#
# ------------------------------------------------------------------------------

# mapping samples to the appropriate function for doing gen-level selections
# This requires an input in src/run.py.
# This runs "gen_selection_Top_semi" under GenSelection.py.
gen_selection_dict = {
    "TT1L2Q": GenSelection.gen_selection_Top_semi,
    # "TTdilep": GenSelection.gen_selection_TTdi,
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

package_path = str(pathlib.Path(__file__).parent.parent.resolve())


class vcbSkimmer(SkimmerABC):
    """
    Skims nanoaod files, saving selected branches and events passing preselection cuts
    (and triggers for data).
    """

    # name in nano files: name in the skimmed output
    skim_vars = {  # noqa: RUF012
        "Jet": {
            **P4,
            "rawFactor": "rawFactor",
            "btagDeepFlavB": "btagDeepFlavB",
            "btagDeepFlavCvB": "btagDeepFlavCvB",
            "btagDeepFlavCvL": "btagDeepFlavCvL",
            "btagDeepFlavQG": "btagDeepFlavQG",
            "btagPNetB": "btagPNetB",  # RobustPrT and chargetagger
            "btagPNetCvB": "btagPNetCvB",
            "btagPNetCvL": "btagPNetCvL",
            "btagPNetCvNotB": "btagPNetCvNotB",
            "btagPNetQvG": "btagPNetQvG",
            "btagPNetTauVJet": "btagPNetTauVJet",
            "ParTPosvsAll": "ParTPosvsAll",
            "ParTNegvsAll": "ParTNegvsAll",
            "ParTPosvsNeg": "ParTPosvsNeg",
            "PflavCharge": "PflavCharge",
            "FlavSplit": "FlavSplit",
            "btagRobustParTAK4B": "btagRobustParTAK4B",
        },
        "MET": {
            "pt": "Pt",
            "phi": "Phi",
        },
        "Lepton": {
            **P4,
            "charge": "charge",
        },
        # "Tau": {
        #     **P4,
        #     "charge": "charge",
        #     "idDeepTau2018v2p5VSjet": "DeepTauvsJet",
        #     "idDeepTau2018v2p5VSmu": "DeepTauvsMu",
        #     "idDeepTau2018v2p5VSe": "DeepTauvsE",
        # },
        # "GenHiggs": P4,
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
    }

    # only applied if fatjet_bb_preselection is True
    preselection = {  # noqa: RUF012
        # roughly, 85% signal efficiency, 2% QCD efficiency (pT: 250-400, mSD:0-250, mRegLegacy:40-250)
        # "pnet-legacy": 0.8,
        # "pnet-v12": 0.3,
        # "glopart-v2": 0.3,
        # at least 1 good iso muon or electron
        # 2btags
    }

    # This is the bjet selection inherited from Clara's default framework.
    bcut = 0.4319
    ak4_bjet_selection = {  # noqa: RUF012
        "pt": 25,
        "eta_max": 2.5,
        "id": "tight",
        "dr_leptons": 0.4,
        "bcut": bcut,
    }

    ak4_bjet_lepton_selection = {  # noqa: RUF012
        "electron_pt": 5,
        "muon_pt": 7,
    }

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
        super().__init__()

        self.XSECS = xsecs if xsecs is not None else {}  # in pb

        # HLT selection
        self.HLTs = {"signal": HLTs.hlt_list(hlt_prefix=False)}
        self.HLTs = self.HLTs[region]
        self._systematics = save_systematics
        self._nano_version = nano_version
        self._region = region
        self._accumulator = processor.dict_accumulator({})
        self._fatjet_bb_preselection = fatjet_bb_preselection
        self._prescale_factor = prescale_factor
        self._fatjet_pt_cut = fatjet_pt_cut

        # CA variablesa
        """
        ca_vars = [
            "mass",
            "msoftdrop",
            "globalParT_massVisApplied",
            "globalParT_massResApplied",
            "particleNet_mass_legacy",
            "isDauTau",
            "dau0_pt",
            "dau1_pt",
            "dau0_eta",
            "dau1_eta",
            "dau0_phi",
            "dau1_phi",
            "dau0_mass",
            "dau1_mass",
            "ntaus_perfatjets",
            "mass_subjets",
            "mass_boostedtaus",
            "nsubjets_perfatjets",
        ]

        self.skim_vars["FatJet"] = {
            **self.skim_vars["FatJet"],
            **{f"CA_{var}": f"CA{var}" for var in ca_vars},
        }

        # update fatjet pT cut
        if fatjet_pt_cut is not None:
            self.fatjet_selection["pt"] = fatjet_pt_cut
        """
        logger.info(
            f"Running skimmer with:\nsystematics {self._systematics}\nregion {self._region}"
        )

    @property
    def accumulator(self):
        return self._accumulator

    def _attach_jetqk_charges(self, events: ak.Array, jets: ak.Array) -> tuple[ak.Array, dict]:
        jetqk_fields = {}
        # If JetQk is already part of the Jet collection, just expose it for output.
        for field in ("QkCharge05", "QkCharge10"):
            if field in ak.fields(jets):
                jetqk_fields[field] = field

        if len(jetqk_fields) == 2:
            return jets, jetqk_fields

        jetqk = None
        try:
            jetqk = events.JetQk
        except Exception:
            try:
                jetqk = events["JetQk"]
            except Exception:
                jetqk = None

        for field in ("QkCharge05", "QkCharge10"):
            if field in jetqk_fields:
                continue

            values = None
            if jetqk is not None and hasattr(jetqk, "fields") and field in jetqk.fields:
                values = jetqk[field]
            else:
                flat_names = (f"JetQk_{field}", f"Jet_{field}")
                for flat_name in flat_names:
                    try:
                        values = events[flat_name]
                        break
                    except Exception:
                        values = getattr(events, flat_name, None)
                    if values is not None:
                        break

            if values is None:
                logger.warning(
                    "Missing %s in input; tried JetQk.%s and %s. Skipping.",
                    field,
                    field,
                    ", ".join((f"JetQk_{field}", f"Jet_{field}")),
                )
                continue

            lengths_match = bool(ak.all(ak.num(values) == ak.num(jets)))
            if not lengths_match:
                logger.warning("Length mismatch for %s; skipping.", field)
                continue

            jets = ak.with_field(jets, values, field)
            jetqk_fields[field] = field

        return jets, jetqk_fields

    def process(self, events: ak.Array):
        """Runs event processor for different types of jets"""

        start = time.time()
        logging.info(f"# events {len(events)}")

        year = events.metadata["dataset"].split("_")[0]
        dataset = "_".join(events.metadata["dataset"].split("_")[1:])
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

        print("starting object selection", f"{time.time() - start:.2f}")

        # Leptons
        num_leptons = 3  # remove this
        electrons, etrigvars = objects.good_electrons(events, events.Electron, year)
        muons, mtrigvars = objects.good_muons(events, events.Muon, year)
        # taus, ttrigvars = objects.good_taus(events, events.Tau, year)
        # boostedtaus = objects.good_boostedtaus(events, events.boostedTau)

        # These are bools saying if the lepton is matched to a trigger object or not
        trigMatchVars = {**etrigvars, **mtrigvars}
        for key, val in trigMatchVars.items():
            trigMatchVars[key] = pad_val(val, num_leptons, False, axis=1).astype(int)

        print("Leptons", f"{time.time() - start:.2f}")

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
        jets, jetqk_skimvars = self._attach_jetqk_charges(events, jets)

        if JEC_loader.met_factory is not None:
            met = JEC_loader.met_factory.build(events.PFMET, jets, {}) if isData else events.PFMET
        else:
            met = events.PFMET

        print("ak4 JECs", f"{time.time() - start:.2f}")

        jets = objects.good_ak4jets(
            jets,
            self._nano_version,
            events,
            muon_pt=self.ak4_bjet_lepton_selection["muon_pt"],
            electron_pt=self.ak4_bjet_lepton_selection["electron_pt"],
            dr_leptons=0.4,
        )
        ht = ak.sum(jets.pt, axis=1)
        print("ak4", f"{time.time() - start:.2f}")

        # AK8 Jetsa
        """
        num_ak8_jets = 3
        fatjets = objects.get_ak8jets(events.FatJet)  # this adds all our extra variables e.g. TXbb
        fatjets, jec_shifted_fatjetvars = JEC_loader.get_jec_jets(
            events,
            fatjets,
            year,
            isData,
            jecs=utils.jecs,
            fatjets=True,
            applyData=True,
            dataset=dataset,
            nano_version=self._nano_version,
        )
        print("ak8 JECs", f"{time.time() - start:.2f}")

        fatjets = objects.good_ak8jets(
            fatjets, **self.fatjet_selection, nano_version=self._nano_version
        )

        # VBF objects
        vbf_jets = objects.vbf_jets(
            jets,
            fatjets[:, :2],
            events,
            **self.vbf_jet_selection,
            **self.vbf_veto_lepton_selection,
        )

        # # AK4 objects away from first two fatjets
        ak4_jets_awayfromak8 = objects.ak4_jets_awayfromak8(
            jets,
            fatjets[:, :2],
            events,
            **self.ak4_bjet_selection,
            **self.ak4_bjet_lepton_selection,
            sort_by="nearest",
        )
        """
        ak4_bjets = objects.ak4_bjet(
            jets,
            events,
            **self.ak4_bjet_selection,
            **self.ak4_bjet_lepton_selection,
        )
        # # JMSR
        # # TODO: add variations per variable
        # bb_jmsr_shifted_vars = get_jmsr(
        #     fatjets_xbb,
        #     2,
        #     jmsr_vars=self.jmsr_vars,
        #     jms_values={key: [1.0, 0.9, 1.1] for key in self.jmsr_vars},
        #     jmr_values={key: [1.0, 0.9, 1.1] for key in self.jmsr_vars},
        #     isData=isData,
        # )

        #########################
        # Save / derive variables
        #########################

        # Gen variables - saving HH and bbbb 4-vector info
        genVars = {}
        for d in gen_selection_dict:
            if d in dataset:
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
        if jetqk_skimvars:
            jet_skimvars = {**jet_skimvars, **jetqk_skimvars}

        ak4JetVars = {
            f"ak4Jet{key}": pad_val(jets[var], num_ak4_jets, axis=1)
            for (var, key) in jet_skimvars.items()
        }
        ak4bTagJetVars = {
            f"ak4bTagJet{key}": pad_val(ak4_bjets[var], 6, axis=1)
            for (var, key) in jet_skimvars.items()
        }

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

        # # JEC and JMSR
        # if self._region == "signal" and isJECs:
        #     # Jet JEC variables
        #     for var in ["pt"]:
        #         key = self.skim_vars["Jet"][var]
        #         for shift, vals in jec_shifted_jetvars[var].items():
        #             if shift != "":
        #                 ak4JetVars[f"ak4Jet{key}_{shift}"] = pad_val(vals, num_ak4_jets, axis=1)

        #     # FatJet JEC variables
        #     for var in ["pt"]:
        #         key = self.skim_vars["FatJet"][var]
        #         for shift, vals in jec_shifted_bbfatjetvars[var].items():
        #             if shift != "":
        #                 bbFatJetVars[f"bbFatJet{key}_{shift}"] = pad_val(vals, 2, axis=1)

        #     # FatJet JMSR
        #     for var in self.jmsr_vars:
        #         key = fatjet_skimvars[var]
        #         bbFatJetVars[f"bbFatJet{key}_raw"] = bbFatJetVars[f"bbFatJet{key}"]
        #         for shift, vals in bb_jmsr_shifted_vars[var].items():
        #             # overwrite saved mass vars with corrected ones
        #             label = "" if shift == "" else "_" + shift
        #             bbFatJetVars[f"bbFatJet{key}{label}"] = vals

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
        eventVars["nBJets"] = ak.num(
            jets[jets.btagRobustParTAK4B >= self.ak4_bjet_selection["bcut"]]
        ).to_numpy()

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
            **ak4bTagJetVars,
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
        add_selection("2bjets", ak.num(ak4_bjets) >= 2, *selection_args)
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

        ######################
        # Weights
        ######################

        totals_dict = {"nevents": n_events}

        if isData:
            skimmed_events["weight"] = np.ones(n_events)
        else:
            weights_dict, totals_temp = self.add_weights(
                events,
                year,
                dataset,
                gen_weights,
                gen_selected,
            )
            skimmed_events = {**skimmed_events, **weights_dict}
            totals_dict = {**totals_dict, **totals_temp}

        ##############################
        # Reshape and apply selections
        ##############################

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
        """Adds weights and variations, saves totals for all norm preserving weights and variations"""
        weights = Weights(len(events), storeIndividual=True)
        weights.add("genweight", gen_weights)

        add_pileup_weight(weights, year, events.Pileup.nPU.to_numpy(), dataset)
        add_ps_weight(weights, events.PSWeight)

        logger.debug("weights", extra=weights._weights.keys())

        ###################### Save all the weights and variations ######################

        # these weights should not change the overall normalization, so are saved separately
        norm_preserving_weights = hh_vars.norm_preserving_weights

        # dictionary of all weights and variations
        weights_dict = {}
        # dictionary of total # events for norm preserving variations for normalization in postprocessing
        totals_dict = {}

        # nominal
        weights_dict["weight"] = weights.weight()

        # norm preserving weights, used to do normalization in post-processing
        weight_np = weights.partial_weight(include=norm_preserving_weights)
        totals_dict["np_nominal"] = np.sum(weight_np[gen_selected])

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

        # TEMP: save each individual weight TODO: remove
        for key in weights._weights:
            weights_dict[f"single_weight_{key}"] = weights.partial_weight([key])

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

        ###################### Normalization (Step 1) ######################

        weight_norm = self.get_dataset_norm(year, dataset)
        # normalize all the weights to xsec, needs to be divided by totals in Step 2 in post-processing
        for key, val in weights_dict.items():
            weights_dict[key] = val * weight_norm

        # save the unnormalized weight, to confirm that it's been normalized in post-processing
        weights_dict["weight_noxsec"] = weights.weight()

        return weights_dict, totals_dict
