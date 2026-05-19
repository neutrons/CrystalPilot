# CORELLI Overview

CORELLI is the elastic diffuse-scattering spectrometer at the Spallation
Neutron Source (SNS) beamline 9 at Oak Ridge National Laboratory.

## What CORELLI is for
CORELLI specialises in measuring the *elastic* component of neutron scattering
from disordered or partially ordered single crystals. The instrument uses a
statistical chopper that imposes a known random modulation on the incident
beam; cross-correlating the modulated incident intensity against the time
structure of the detected scattering separates the truly elastic events from
inelastic background. This makes CORELLI particularly suited to:

- Diffuse scattering from short-range-ordered systems
- Magnetic diffuse scattering
- Single-crystal scattering studies where strong inelastic backgrounds
  contaminate conventional measurements

## Beam parameters
- Wavelength range: roughly 0.7 to 2.89 Å (white-beam Laue with a stat chopper)
- Detector coverage: large position-sensitive detector array around the sample
- Sample stage: two-axis goniometer (omega + phi); cryostat / furnace / magnet
  options for typical SE configurations

## Data flow
1. Raw event data is written to `/SNS/CORELLI/IPTS-<N>/nexus/`.
2. Live reduction outputs land in
   `/SNS/CORELLI/IPTS-<N>/shared/autoreduce/live_data/`.
3. UB matrices refined from live monitoring are saved to
   `/SNS/CORELLI/IPTS-<N>/shared/CrystalPilot/live-data-monitoring/`.

This document is a placeholder. Real CORELLI operating procedures, PV
mappings, and reduction recipes should be ingested from beamline scientists
before relying on this knowledge base in production.
