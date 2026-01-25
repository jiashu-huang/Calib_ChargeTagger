"""
Gen selection functions for skimmer.

Author(s): Raghav Kansal
"""

from __future__ import annotations

import awkward as ak
import numpy as np
from boostedhh.processors.utils import (
    GEN_FLAGS,
    P4,
    PDGID,
    add_selection,
    pad_val,
)
from coffea.nanoevents.methods.base import NanoEventsArray
from coffea.nanoevents.methods.nanoaod import (
    ElectronArray,
    FatJetArray,
    JetArray,
    MuonArray,
)

TOP_PDGID = 6
W_PDGID = 24
LepArray = ElectronArray | MuonArray


def _iterate_children(children, parent_pdgId):
    """Iterates through the children of a particle in case of photon scattering to find the final daughter particles"""

    for _ in range(5):
        # check if any of the children are the same as the parent pdgId
        mask = ak.any(np.abs(children.pdgId) == parent_pdgId, axis=2)
        if not ak.any(mask):
            break

        children_children = ak.flatten(
            children[np.abs(children.pdgId) == parent_pdgId].children, axis=3
        )

        # get next layer of children
        children = ak.where(mask, children_children, children)

    return children


def _sum_taus(taut):
    return ak.sum(taut, axis=1)


def gen_selection_Top(
    events: NanoEventsArray,
    jets: JetArray,  # noqa: ARG001
    fatjets: FatJetArray,
    selection_args: list,  # noqa: ARG001
    skim_vars: dict,
    fatjet_str: str,
):
    """Get Hadronic Top and children information"""
    assert fatjet_str in [
        "bbFatJet",
        "ak8FatJet",
    ], "fatjet_str parameter must be bbFatJet or ak8FatJet"

    # finding tops
    tops = events.GenPart[
        (abs(events.GenPart.pdgId) == TOP_PDGID) * events.GenPart.hasFlags(GEN_FLAGS)
    ]
    GenTopVars = {f"GenTop{key}": tops[var].to_numpy() for (var, key) in skim_vars.items()}

    daughters = ak.flatten(tops.distinctChildren, axis=2)
    daughters = daughters[daughters.hasFlags(["fromHardProcess", "isLastCopy"])]
    daughters_pdgId = abs(daughters.pdgId)
    print("daughters", daughters[(daughters_pdgId == W_PDGID)])
    wboson_0 = ak.firsts(daughters[(daughters_pdgId == W_PDGID)][:, 0:1])
    wboson_1 = ak.firsts(daughters[(daughters_pdgId == W_PDGID)][:, 1:2])
    GenTopVars = {
        **GenTopVars,
        **{f"GenTopW0{key}": wboson_0[var].to_numpy() for (var, key) in skim_vars.items()},
        **{f"GenTopW1{key}": wboson_1[var].to_numpy() for (var, key) in skim_vars.items()},
    }

    wboson_daughters = ak.flatten(daughters[(daughters_pdgId == W_PDGID)].distinctChildren, axis=2)
    wboson_daughters = wboson_daughters[
        wboson_daughters.hasFlags(["fromHardProcess", "isLastCopy"])
    ]

    bquark = daughters[(daughters_pdgId == 5)]
    matched_to_top = fatjets.metric_table(tops) < 0.8
    is_fatjet_matched = ak.any(matched_to_top, axis=2)

    qs_0 = ak.firsts(wboson_daughters[:, 0:1])
    qs_1 = ak.firsts(wboson_daughters[:, 1:2])
    qs_2 = ak.firsts(wboson_daughters[:, 2:3])
    qs_3 = ak.firsts(wboson_daughters[:, 3:4])
    bs_0 = ak.firsts(bquark[:, 0:1])
    bs_1 = ak.firsts(bquark[:, 1:2])

    numtop1 = ak.values_astype(fatjets.delta_r(qs_0) < 0.8, np.int32) + ak.values_astype(
        fatjets.delta_r(qs_1) < 0.8, np.int32
    )
    numtop2 = ak.values_astype(fatjets.delta_r(qs_2) < 0.8, np.int32) + ak.values_astype(
        fatjets.delta_r(qs_3) < 0.8, np.int32
    )

    fatjets["TopMatch"] = is_fatjet_matched
    fatjets["TopMatchIndex"] = ak.mask(
        ak.argmin(fatjets.metric_table(tops), axis=2), fatjets["TopMatch"] == 1
    )
    fatjets["NumBMatchedTop1"] = ak.values_astype(fatjets.delta_r(bs_0) < 0.8, np.int32)
    fatjets["NumBMatchedTop2"] = ak.values_astype(fatjets.delta_r(bs_1) < 0.8, np.int32)
    fatjets["NumQMatchedTop1"] = numtop1
    fatjets["NumQMatchedTop2"] = numtop2

    num_fatjets = 2
    FatJetVars = {
        f"{fatjet_str}{var}": pad_val(fatjets[var], num_fatjets, axis=1)
        for var in [
            "TopMatch",
            "TopMatchIndex",
            "NumBMatchedTop1",
            "NumBMatchedTop2",
            "NumQMatchedTop1",
            "NumQMatchedTop2",
        ]
    }

    return {**GenTopVars, **FatJetVars}


def gen_selection_Top_semi(
    events: NanoEventsArray,
    jets: JetArray,
    electrons: LepArray,
    muons: LepArray,
    selection_args: list,  # noqa: ARG001
    skim_vars: dict,
):

    # finding tops
    tops = events.GenPart[
        (abs(events.GenPart.pdgId) == TOP_PDGID) * events.GenPart.hasFlags(GEN_FLAGS)
    ]
    GenTopVars = {f"GenTop{key}": tops[var].to_numpy() for (var, key) in skim_vars.items()}

    daughters = ak.flatten(tops.distinctChildren, axis=2)
    daughters = daughters[daughters.hasFlags(["fromHardProcess", "isLastCopy"])]
    daughters_pdgId = abs(daughters.pdgId)

    wboson_0 = ak.firsts(daughters[(daughters_pdgId == W_PDGID)][:, 0:1])
    wboson_1 = ak.firsts(daughters[(daughters_pdgId == W_PDGID)][:, 1:2])
    GenTopVars = {
        **GenTopVars,
        **{f"GenTopW0{key}": wboson_0[var].to_numpy() for (var, key) in skim_vars.items()},
        **{f"GenTopW1{key}": wboson_1[var].to_numpy() for (var, key) in skim_vars.items()},
    }

    wbosons = daughters[(daughters_pdgId == W_PDGID)]
    wboson_children = wbosons.distinctChildren
    wboson_children = wboson_children[wboson_children.hasFlags(["fromHardProcess", "isLastCopy"])]
    wboson_children_pdgId = abs(wboson_children.pdgId)

    w_has_b = ak.any(wboson_children_pdgId == 5, axis=2)
    w_has_c = ak.any(wboson_children_pdgId == 4, axis=2)
    w_bc_mask = w_has_b & w_has_c
    w_to_bc = ak.any(w_bc_mask, axis=1)

    w_bc_children = wboson_children[w_bc_mask]
    w_bc_b = ak.flatten(w_bc_children[abs(w_bc_children.pdgId) == 5], axis=2)

    wboson_daughters = ak.flatten(wboson_children, axis=2)
    wboson_daughters_pdgId = abs(wboson_daughters.pdgId)

    bquark = daughters[(daughters_pdgId == 5)]
    # matched_to_top = fatjets.metric_table(tops) < 0.8
    # is_fatjet_matched = ak.any(matched_to_top, axis=2)

    # lepdecay = wboson_daughters[(wboson_daughters_pdgId == 13) or (wboson_daughters_pdgId ==11 ) ]

    lep_mask = (wboson_daughters_pdgId == 11) | (wboson_daughters_pdgId == 13)
    lep_nu_mask = (
        (wboson_daughters_pdgId == 11)
        | (wboson_daughters_pdgId == 13)
        | (wboson_daughters_pdgId == 12)
        | (wboson_daughters_pdgId == 14)
    )
    lepdecay = wboson_daughters[lep_mask]
    ls_0 = ak.firsts(lepdecay[:, 0:1])  # first lepton per event/top
    #    all_local_indices = ak.local_index(wboson_daughters, axis =1)
    print(lep_mask)
    print(lep_nu_mask)
    # lep_indices = all_local_indices[lep_mask]
    # print(lep_indices)

    non_lep_nu_mask = ~lep_nu_mask

    quark_daughters = wboson_daughters[non_lep_nu_mask]
    print(quark_daughters)
    qs_2 = ak.firsts(quark_daughters[:, 0:1])
    qs_3 = ak.firsts(quark_daughters[:, 1:2])
    bs_0 = ak.firsts(bquark[:, 0:1])
    bs_1 = ak.firsts(bquark[:, 1:2])

    GenTopBVars = {
        **{f"GenTopB0{key}": bs_0[var].to_numpy() for (var, key) in skim_vars.items()},
        **{f"GenTopB1{key}": bs_1[var].to_numpy() for (var, key) in skim_vars.items()},
    }
    GenWbcVars = {
        **{
            f"GenWb{key}": pad_val(w_bc_b[var], 1, axis=1)[:, 0] for (var, key) in skim_vars.items()
        },
        "GenWtoBC": w_to_bc.to_numpy(),
    }

    GenQVars = {
        **{f"GenQ1{key}": qs_2[var].to_numpy() for (var, key) in skim_vars.items()},
        **{f"GenQ2{key}": qs_3[var].to_numpy() for (var, key) in skim_vars.items()},
        "GenQ1PdgId": qs_2.pdgId.to_numpy(),
        "GenQ2PdgId": qs_3.pdgId.to_numpy(),
    }

    # fatjets["TopMatch"] = is_fatjet_matched
    # fatjets["TopMatchIndex"] = ak.mask(
    #    ak.argmin(fatjets.metric_table(tops), axis=2), fatjets["TopMatch"] == 1
    # )
    jets["NumBMatchedTop1"] = ak.values_astype(jets.delta_r(bs_0) < 0.4, np.int32)
    jets["NumBMatchedTop2"] = ak.values_astype(jets.delta_r(bs_1) < 0.4, np.int32)
    electrons["NumlMatchedTop1"] = ak.values_astype(electrons.delta_r(ls_0) < 0.2, np.int32)
    muons["NumlMatchedTop1"] = ak.values_astype(muons.delta_r(ls_0) < 0.2, np.int32)
    jets["NumQMatchedTop1"] = ak.values_astype(jets.delta_r(qs_2) < 0.4, np.int32)
    jets["NumQMatchedTop2"] = ak.values_astype(jets.delta_r(qs_3) < 0.4, np.int32)

    num_jets = 6
    JetVars = {
        f"ak4{var}": pad_val(jets[var], num_jets, axis=1)
        for var in [
            # "TopMatch",
            # "TopMatchIndex",
            "NumBMatchedTop1",
            "NumBMatchedTop2",
            "NumQMatchedTop1",
            "NumQMatchedTop2",
        ]
    }
    num_lep = 3
    EleVars = {
        f"electrons{var}": pad_val(electrons[var], num_lep, axis=1)
        for var in [
            "NumlMatchedTop1",
        ]
    }

    MuonVars = {  # noqa: F841
        f"muons{var}": pad_val(muons[var], num_lep, axis=1)
        for var in [
            "NumlMatchedTop1",
        ]
    }

    return {**GenTopVars, **JetVars, **EleVars, **GenTopBVars, **GenWbcVars, **GenQVars}


def gen_selection_HHbbtautau(
    events: NanoEventsArray,
    fatjets: FatJetArray,  # noqa: ARG001
    selection_args: list,
):
    """Gets HH, bb, and tautau 4-vectors + tau decay information"""

    genparts = events.GenPart[events.GenPart.hasFlags(GEN_FLAGS)]

    # finding the two gen higgs
    higgs = genparts[genparts.pdgId == PDGID.H]

    # saving 4-vector info
    GenHiggsVars = {f"GenHiggs{key}": higgs[var].to_numpy() for (var, key) in P4.items()}

    # saving whether H->bb or H->tautau
    higgs_children = higgs.children
    # pad_val is necessary to avoid a numpy MaskedArray even though all events have exactly 2 Higgs'
    GenHiggsVars["GenHiggsChildren"] = pad_val(higgs_children.pdgId[:, :, 0], 2, axis=1)

    # finding bb and VV children
    is_bb = np.abs(higgs_children.pdgId) == PDGID.b
    is_tt = np.abs(higgs_children.pdgId) == PDGID.tau

    # checking that there are 2 bs and 2 taus
    has_bb = ak.sum(ak.flatten(is_bb, axis=2), axis=1) == 2
    has_tt = ak.sum(ak.flatten(is_tt, axis=2), axis=1) == 2
    if selection_args is not None:
        add_selection("has_bbtautau", has_bb * has_tt, *selection_args)

    bb = ak.flatten(higgs_children[is_bb], axis=2)
    GenbbVars = {f"Genbb{key}": pad_val(bb[var], 2, axis=1) for (var, key) in P4.items()}

    taus = higgs_children[is_tt]
    flat_taus = ak.flatten(taus, axis=2)
    GenTauVars = {f"GenTau{key}": pad_val(flat_taus[var], 2, axis=1) for (var, key) in P4.items()}

    tau_children = ak.flatten(taus.children, axis=2)
    tau_children = _iterate_children(tau_children, PDGID.tau)

    # check if tau children are leptons or hadrons
    # check neutral and charged pion IDs for hadronic taus
    tauh = _sum_taus(
        ak.any([ak.any(np.abs(tau_children.pdgId) == pid, axis=2) for pid in PDGID.pions], axis=0)
    )
    taumu = _sum_taus(ak.any(np.abs(tau_children.pdgId) == PDGID.mu, axis=2))
    taue = _sum_taus(ak.any(np.abs(tau_children.pdgId) == PDGID.e, axis=2))

    GenTauVars["GenTauhh"] = (tauh == 2).to_numpy()
    GenTauVars["GenTauhm"] = ((tauh == 1) & (taumu == 1)).to_numpy()
    GenTauVars["GenTauhe"] = ((tauh == 1) & (taue == 1)).to_numpy()

    # fatjet gen matching
    # Hbb = higgs[ak.sum(is_bb, axis=2) == 2]
    # Hbb = ak.pad_none(Hbb, 1, axis=1, clip=True)[:, 0]

    # Htt = higgs[ak.sum(is_tt, axis=2) == 2]
    # Htt = ak.pad_none(Htt, 1, axis=1, clip=True)[:, 0]

    # TODO: check more than just the leading two fatjets!
    # bbdr = fatjets[:, :2].delta_r(Hbb)
    # ttdr = fatjets[:, :2].delta_r(Htt)

    # match_dR = 0.8
    # Hbb_match = bbdr <= match_dR
    # Htt_match = ttdr <= match_dR

    # # overlap removal - in the case where fatjet is matched to both, match it only to the closest Higgs
    # Hbb_match = (Hbb_match * ~Htt_match) + (bbdr <= ttdr) * (Hbb_match * Htt_match)
    # Htt_match = (Htt_match * ~Hbb_match) + (bbdr > ttdr) * (Hbb_match * Htt_match)

    # GenMatchingVars = {
    #     "ak8FatJetHbb": pad_val(Hbb_match, 2, axis=1),
    #     "ak8FatJetHtt": pad_val(Htt_match, 2, axis=1),
    # }

    return {**GenHiggsVars, **GenbbVars, **GenTauVars}  # , **GenMatchingVars}


def gen_selection_HH4b(
    events: NanoEventsArray,
    fatjets: FatJetArray,  # noqa: ARG001
    selection_args: list,  # noqa: ARG001
):
    """
    Save GenVars for HH(4b) events
    """
    genparts = events.GenPart[events.GenPart.hasFlags(GEN_FLAGS)]

    # finding the two gen higgs
    higgs = genparts[genparts.pdgId == PDGID.H]
    GenHiggsVars = {f"GenHiggs{key}": higgs[var].to_numpy() for (var, key) in P4.items()}
    higgs_children = higgs.children
    is_bb = np.abs(higgs_children.pdgId) == PDGID.b
    bs = ak.flatten(higgs_children[is_bb], axis=2)
    GenbVars = {f"Genb{key}": pad_val(bs[var], 4, axis=1) for (var, key) in P4.items()}

    return {**GenHiggsVars, **GenbVars}
