# Active Beamline: CORELLI (SNS BL-9)

CORELLI is the elastic diffuse-scattering spectrometer at the Spallation
Neutron Source (SNS), Oak Ridge National Laboratory, beamline 9 (BL-9). It
uses a statistical-chopper cross-correlation technique to separate the
elastic component of the scattering from the inelastic background, giving
high-quality diffuse-scattering maps from disordered single crystals.

**Instrument specifics:**
- Wavelength band: ~0.7 – 2.89 Å (statistical chopper, white-beam Laue)
- Sample environment: cryostat, furnace, magnet, gas-pressure cell options
- Goniometer: two-axis (omega + phi) ambient sample stage

**Workflow notes for CORELLI users:**
- IPTS data lives under `/SNS/CORELLI/IPTS-<N>/`.
- Default preset for typical SCD work: `corelli_standard`.
- EIC submissions land in `/SNS/groups/corelli/bl_9/IPTS-<N>/`.

When users ask about CORELLI-specific operating procedures, diffuse-scattering
data treatment, or the cross-correlation method, call `retrieve_docs` against
the CORELLI knowledge base before answering.
