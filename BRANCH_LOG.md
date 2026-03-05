# Branch log: lep-overlap

We understand that the following code in vcbSkimmer.py drops a lot of b-tagged jets:

```python
ak4_bjet_lepton_selection = {  # noqa: RUF012
    "electron_pt": 5,
    "muon_pt": 7,
}
```

along with

```python
jets = objects.good_ak4jets(
    jets,
    self._nano_version,
    events,
    muon_pt=self.ak4_bjet_lepton_selection["muon_pt"],
    electron_pt=self.ak4_bjet_lepton_selection["electron_pt"],
    dr_leptons=0.4,
)
```

The goal of this branch is to remove that lepton selection on jets.

Bigger picture: we are studying **pp -> tt, (t -> bW, W -> cb), (t -> bW, W -> l nu)**. Only the hard lepton from `(t -> bW, W -> l nu)` matters.

## Attempt 1: HLT (implemented)

We will apply the dR < 0.4 overlap removal only against the lepton in **t -> bW, W -> l nu**.
Our analysis uses HLT triggers IsoMu24 / Ele32, so we will use these in our analysis too.
In short, we will perform overlap removal against the prompt lepton.
* Each event should have a prompt lepton that fires either IsoMu24 (and is a Muon) or Ele32 (and is an electron). Our cut-off is: pT >= 25 GeV for IsoMu24, pT >= 35 GeV for Ele32.
* In the NanoAOD file, IsoMu24 is stored as "HLT_IsoMu24", while Ele32 is stored as "HLT_Ele32_WPTight_Gsf".
* One could apply tight ID selection on the prompt lepton.
* One should also check the isolation of the prompt lepton.
* If an event does not have the HLT triggers IsoMu24 or Ele32 fired, the processor should discard the event.

### Implementation

**Files changed:**

1. **`src/processors/objects.py`** (`good_ak4jets`):
   - Added optional parameters `cleaning_electrons` and `cleaning_muons`.
   - When provided, overlap removal uses these collections instead of all NanoAOD leptons above the pT floor.
   - When not provided, behavior is unchanged (backward compatible).

2. **`src/processors/vcbSkimmer.py`**:
   - After building good electrons/muons (which already include trigger matching via `trig_match_sel`), extract the trigger-matched subset:
     - `prompt_electrons = electrons[etrigvars["ElectronTrigMatchEGamma"]]` — good electrons matched to Ele32_WPTight_Gsf with pT > 31 GeV.
     - `prompt_muons = muons[mtrigvars["MuonTrigMatchMuon"]]` — good muons matched to IsoMu24 with pT > 26 GeV.
   - Pass `prompt_electrons` and `prompt_muons` as `cleaning_electrons`/`cleaning_muons` to `good_ak4jets`.
   - Replaced the old `apply_trigger = False` block with a `single_lep_trigger` selection requiring `HLT_IsoMu24 | HLT_Ele32_WPTight_Gsf`. Events failing both are dropped.

**What this means:**
- Jet-lepton overlap removal now only removes jets near the prompt, trigger-matched, analysis-quality lepton — not near every soft electron > 5 GeV or muon > 7 GeV.
- The prompt lepton already passes tight ID (mvaIso_WP90 for electrons, tightId + pfRelIso04 < 0.15 for muons) because it comes from the `good_electrons`/`good_muons` collections.
- Events where neither single-lepton trigger fired are discarded. This does NOT affect `finalWeight` normalization: `np_nominal` is computed over all input events before any selection cuts.

## 2026-03-04

Primary analysis output ROOT file on this `lep-overlap` branch:

`/home/jhuan166/Vcb/Calib_ChargeTagger/nano_skim_all_merged_000_024_lep-overlap_uptodate_20260304_lz4.root`

This is the correctly processed output `.root` file and should be used for primary analysis.

Sample/weight note:
- It comprises about 10% of all input events.
- Each event therefore basically carries a `10x` effective weight in full-dataset normalization.
