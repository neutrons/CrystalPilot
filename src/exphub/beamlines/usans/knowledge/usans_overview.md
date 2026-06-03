# USANS Overview

USANS is the ultra-small-angle neutron scattering instrument at the Spallation
Neutron Source (SNS) beamline 1A (BL-1A) at Oak Ridge National Laboratory.

## What USANS is for
USANS measures neutrons scattered through *very* small angles, extending the
accessible structural length scale beyond conventional SANS — roughly 0.1 to
20 microns. It is well suited to:

- Large-scale structure in porous media, rocks, and cements
- Phase domains, voids, and precipitates on the micron scale
- Hierarchical structure when combined (merged) with conventional SANS to
  cover a wide continuous Q-range

USANS is the low-Q complement to SANS; the two are routinely merged into a
single I(Q) curve spanning several decades in Q.

## Instrument geometry
USANS uses a **Bonse-Hart double-crystal** setup rather than an area detector:
- A perfect-crystal (e.g. triple-bounce Si) monochromator defines a highly
  collimated, narrow-divergence incident beam.
- A matched perfect-crystal analyser is rocked through the Bragg condition; the
  rocking curve recorded versus analyser angle is converted to I(Q).
- Because the resolution function is a slit (not a pinhole), raw USANS data are
  **slit-smeared**; de-smearing is part of reduction.

## Beam parameters
- Q-range: ultra-low Q (down to ~1e-5 1/Angstrom), overlapping SANS at the
  high-Q end.
- These values, plus the incident wavelength band and exact resolution, are
  **provisional** here and should be confirmed with the BL-1A scientist.

## Data flow
1. Raw data is written under `/SNS/USANS/IPTS-<N>/`.
2. Reduction (rocking curve to de-smeared I(Q), and merging with SANS) is done
   in Mantid (USANS reduction); CrystalPilot does not yet run this pipeline —
   the I(Q) Reduction tab is a placeholder and the prediction-model dropdown
   reads "TBD".

## Provisional values
This document is a placeholder. The real USANS EIC server, beamline PVs,
wavelength band, resolution, EIC strategy-CSV column layout, and reduction
recipes are TBD and should be ingested from the BL-1A beamline scientist before
relying on this knowledge base in production.
