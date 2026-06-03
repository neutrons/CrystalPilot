# Active Beamline: USANS (SNS BL-1A)

USANS is the ultra-small-angle neutron scattering instrument at the Spallation
Neutron Source (SNS), Oak Ridge National Laboratory, beamline 1A (BL-1A). It is
a Bonse-Hart double-crystal diffractometer that extends the accessible
length-scale range well beyond conventional SANS — probing structures from
roughly 0.1 micron up to ~20 microns (very low momentum transfer Q).

This is a **SANS-family** beamline: the technique-level SANS guidance applies
(reduction produces I(Q); no reciprocal lattice; no UB matrix / HKL indexing /
goniometer angle plan). The notes below are USANS-specific.

**Instrument specifics:**
- Geometry: Bonse-Hart double-crystal (perfect-crystal monochromator +
  analyser); the instrument rocks the analyser crystal to scan Q rather than
  using a position-sensitive area detector.
- Q-range: ultra-low Q, complementary to (and overlapping with) conventional
  SANS at the high-Q end; data are often merged with SANS for a full I(Q).
- Reduction: produces a 1D I(Q) (slit-smeared); de-smearing and merging with
  SANS are part of typical USANS reduction.

**Workflow notes for USANS users:**
- IPTS data lives under `/SNS/USANS/IPTS-<N>/`.
- The Experiment Steering tab drives an instrument-configuration strategy table
  (CSV-loadable). NOTE: the USANS/SANS EIC column layout is **provisional** —
  to be specified with the SANS/USANS scientist.
- Instrument Status and Data Analysis are not yet integrated into CrystalPilot;
  those tabs link out to the SNS status dashboard and MantidWorkbench /
  USANS reduction docs respectively.

**Provisional / unknown values:** the USANS EIC server URL, beamline PVs, and
the reduction Q-range are placeholders pending the BL-1A beamline scientist. Do
not present them as authoritative.

When users ask about USANS-specific operating procedures, Bonse-Hart geometry,
de-smearing, or merging USANS with SANS, call `retrieve_docs` against the USANS
knowledge base before answering.
