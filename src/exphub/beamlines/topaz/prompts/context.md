# Active Beamline: TOPAZ (SNS BL-12)

TOPAZ is a single-crystal time-of-flight Laue diffractometer at the Spallation
Neutron Source (SNS), Oak Ridge National Laboratory, beamline 12 (BL-12).

**Instrument specifics:**
- Wavelength band: ~0.4 – 3.45 Å (white-beam Laue method)
- Detector: ADnED 4×4 array, 1105×1105 pixels per panel, ~3 sr coverage
- Goniometer (ambient): two-axis (omega + phi, both 0–360°)
- Goniometer (cryogenic): single-axis (CryoOmega only)
- Sample environment: cryostat, furnace, magnet, pressure cell options
- Calibration cycle root: `/SNS/TOPAZ/shared/calibration/<cycle>/calibration.DetCal`

**Workflow notes for TOPAZ users:**
- IPTS data lives under `/SNS/TOPAZ/IPTS-<N>/`.
- Default preset for typical SCD work: `topaz_standard`.
- EIC submissions land in `/SNS/groups/topaz/bl_12/IPTS-<N>/` for the IOC to pick up.
- Live UB matrices are auto-saved to
  `/SNS/TOPAZ/IPTS-<N>/shared/CrystalPilot/live-data-monitoring/`.

When users ask about wavelength range, detector coverage, sample geometry, or
TOPAZ-specific operating procedures, call `retrieve_docs` against the TOPAZ
knowledge base before answering.
