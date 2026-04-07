# CrystalPilot Beamline Knowledge Guide

Reference document for the CrystalPilot agent covering neutron diffraction
instruments at ORNL, crystallographic concepts, and experiment configuration.

---

## Single-Crystal Neutron Diffraction Overview

Single-crystal neutron diffraction is a technique for determining the atomic
and magnetic structure of crystalline materials. A single crystal is placed in
a neutron beam; scattered neutrons are recorded by area detectors. The pattern
of Bragg peaks encodes the crystal's unit cell, symmetry, and atomic positions.

Neutrons are sensitive to light elements (hydrogen, lithium, oxygen) and to
magnetic moments, making neutron diffraction complementary to X-ray
diffraction. ORNL's Spallation Neutron Source (SNS) and High Flux Isotope
Reactor (HFIR) host several world-class single-crystal diffractometers.

Key quantities:
- **d-spacing**: interplanar spacing in Angstroms (A); related to scattering
  angle by Bragg's law: n*lambda = 2d*sin(theta)
- **Q (momentum transfer)**: Q = 4*pi*sin(theta)/lambda = 2*pi/d; measured in inverse Angstroms
- **Wavelength (lambda)**: neutron wavelength in A; at SNS instruments the full
  white-beam polychromatic spectrum is used (Laue method)
- **UB matrix**: 3x3 matrix relating crystal lattice vectors to laboratory
  coordinates; required for peak indexing and prediction

---

## Crystal Systems and Bravais Lattices

There are seven crystal systems defined by the metric symmetry of the unit cell:

| System | Constraints |
|--------|-------------|
| Cubic | a = b = c, alpha = beta = gamma = 90 deg |
| Tetragonal | a = b != c, alpha = beta = gamma = 90 deg |
| Orthorhombic | a != b != c, alpha = beta = gamma = 90 deg |
| Monoclinic | a != b != c, alpha = gamma = 90 deg, beta != 90 deg |
| Triclinic | a != b != c, alpha != beta != gamma != 90 deg |
| Trigonal/Rhombohedral | a = b = c, alpha = beta = gamma != 90 deg |
| Hexagonal | a = b != c, alpha = beta = 90 deg, gamma = 120 deg |

Centering types (lattice centering):
- **P** (Primitive): lattice points at corners only
- **I** (Body-centered): additional point at cell center (a+b+c)/2
- **F** (Face-centered): additional points at all face centers
- **A, B, C** (Base-centered): additional point on one pair of faces
- **R** (Rhombohedral): for trigonal/hexagonal; obverse/reverse settings
  (Robv and Rrev)
- **H**: hexagonal primitive

The 14 Bravais lattices combine crystal system + centering. Centering imposes
systematic absences on the diffraction pattern.

### Crystal System to Point Group to Centering Cascade

When configuring CrystalPilot, you first choose the **crystal system**, which
determines the list of valid **point groups**. Choosing the point group then
determines the list of valid **centering** types. This is a strict cascade:
changing the crystal system invalidates the current point group and centering.

Valid point groups by crystal system:
- Triclinic: 1, -1
- Monoclinic: 2, m, 2/m, 112, 11m, 112/m
- Orthorhombic: 222, mm2, mmm
- Tetragonal: 4, -4, 4/m, 422, 4mm, -42m, -4m2, 4/mmm
- Trigonal/Rhombohedral: 3 r, -3 r, 32 r, 3m r, -3m r
- Trigonal/Hexagonal: 3, -3, 312, 31m, 32, 321, 3m, -31m, -3m, -3m1
- Hexagonal: 6, -6, 6/m, 622, 6mm, -62m, -6m2, 6/mmm
- Cubic: 23, m-3, 432, -43m, m-3m

Valid centering by point group:
- Triclinic point groups (1, -1): P only
- Monoclinic point groups (2, m, 2/m, etc.): P, C
- Orthorhombic (222, mm2, mmm): P, I, C, A, B
- Tetragonal (4, -4, ..., 4/mmm): P, I
- Trigonal/Rhombohedral (3 r, -3 r, etc.): R
- Trigonal/Hexagonal (3, -3, etc.): Robv, Rrev
- Hexagonal (6, -6, ..., 6/mmm): P
- Cubic (23, m-3, 432, -43m, m-3m): P, I, F

Call `refresh_schema` after changing the crystal system so the agent sees
the updated centering and point group lists.

---

## Point Groups, Space Groups, and Laue Classes

A **point group** describes the rotational symmetry of a crystal; there are
32 crystallographic point groups. The **space group** adds translation
symmetry (screw axes, glide planes); there are 230 space groups.

The **Laue class** (11 centrosymmetric point groups) is what is directly
observable in a diffraction experiment because the diffraction pattern always
has inversion symmetry (Friedel's law). For example:
- Crystal system Cubic, point group m-3m -> Laue class m-3m
- Tetragonal, 4/mmm -> Laue class 4/mmm

---

## Unit Cell Volume Sanity Check

When configuring an experiment, the molecular formula, Z (number of formula
units), and unit cell volume should be physically consistent. A reasonable
rule of thumb: volume should be at least atoms * Z * 10 cubic Angstroms.
For example, NaCl (2 atoms) with Z=4 should have volume >= 80 cubic Angstroms.

If the unit cell volume seems unrealistically small for the given formula and
Z, double-check:
- Is the formula correct? Include all atoms (e.g. C6H12O6 not just C6O6).
- Is Z correct? For simple salts Z is often 2 or 4; for organics Z is often
  1, 2, or 4.
- Are the lattice parameters entered in Angstroms (not nanometers)?

---

## TOPAZ Instrument (SNS BL-12)

TOPAZ is a time-of-flight (TOF) single-crystal Laue diffractometer at the
Spallation Neutron Source. It uses the full white-beam polychromatic neutron
spectrum and a large array of flat panel detectors.

**Typical operating parameters:**
- Wavelength range: 0.4 -- 3.45 A
- Maximum Q: ~17 inverse Angstroms (atomic resolution, small unit cells)
- d-spacing range: 0.499 -- 11.0 A
- Peak finding: ~500 peaks recommended
- Peak integration radius: ~0.11
- Background inner/outer radius: ~0.115 / ~0.14
- Tolerance for indexing: 0.12

TOPAZ excels at high-resolution studies of materials with small-to-medium
unit cells. Its wide wavelength and Q coverage make it suitable for precise
atomic coordinate determination, charge density studies, and hydrogen atom
location.

Standard preset: `topaz_standard` in CrystalPilot.

---

## CORELLI Instrument (SNS BL-9)

CORELLI is an elastic diffuse-scattering spectrometer and single-crystal
diffractometer using a statistical chopper system. It is optimized for
diffuse scattering and structural disorder studies but also used for standard
single-crystal work.

**Typical operating parameters:**
- Wavelength range: 0.7 -- 2.89 A
- Maximum Q: ~14 inverse Angstroms
- d-spacing range: 0.5 -- 10.0 A
- Peak finding: ~300 peaks recommended
- Peak integration radius: ~0.13
- Background inner/outer radius: ~0.135 / ~0.16
- Tolerance for indexing: 0.15

CORELLI's energy-discriminating capability via the correlation chopper
separates elastic from inelastic scattering, useful for diffuse scattering
from disordered materials.

Standard preset: `corelli_standard` in CrystalPilot.

---

## MANDI Instrument (SNS BL-11B)

MANDI (Macromolecular Neutron Diffractometer) is designed for large-unit-cell
materials including proteins and other macromolecules. It uses long-wavelength
neutrons and operates at low Q ranges.

**Typical operating parameters:**
- Wavelength range: 0.8 -- 4.0 A
- Maximum Q: ~10 inverse Angstroms
- d-spacing range: 0.7 -- 7.0 A
- Peak finding: ~200 peaks recommended
- Tolerance for indexing: 0.10

MANDI is the choice for biological macromolecules (proteins, nucleic acids),
large pharmaceutical molecules, and other systems with large unit cells.
Long wavelengths reduce background and improve contrast for hydrogen.

Standard preset: `mandi_standard` in CrystalPilot.

---

## DEMAND Instrument (HFIR HB-3A)

DEMAND (formerly HB-3A) is a four-circle single-crystal diffractometer at
HFIR. Unlike the TOF instruments at SNS, DEMAND uses a monochromatic neutron
beam with a bent Si-220 monochromator.

**Key characteristics:**
- Monochromatic operation with selectable wavelength
- Four-circle geometry (two-theta, omega, chi, phi) for full reciprocal
  space coverage
- 2D area detector
- Optimized for small samples and high-pressure experiments
- Excellent for magnetic structure determination at low temperatures
- Ideal for extreme-condition experiments (pressure cells, cryomagnets)

DEMAND is the preferred choice when samples are very small, when full
orientation control is needed (e.g. magnetic field experiments), or when
monochromatic data collection is preferred over Laue methods.

---

## IMAGINE Instrument (HFIR CG-4D)

IMAGINE is a quasi-Laue single-crystal neutron diffractometer at HFIR. It
uses a broad-bandpass beam and cylindrical image plate detectors for
efficient data collection.

**Key characteristics:**
- Quasi-Laue technique with broad wavelength band (2-4 A typical)
- Cylindrical image plate detectors providing large solid angle coverage
- Optimized for macromolecular crystallography
- Suitable for unit cells up to ~150 A
- Lower flux than MANDI but complements SNS with reactor-based neutrons

IMAGINE is used for protein crystallography and other macromolecular
systems where the quasi-Laue technique provides efficient sampling of
reciprocal space.

---

## Instrument Comparison Summary

| Parameter | TOPAZ (SNS) | CORELLI (SNS) | MANDI (SNS) | DEMAND (HFIR) | IMAGINE (HFIR) |
|-----------|-------------|---------------|-------------|---------------|----------------|
| Method | TOF Laue | TOF + chopper | TOF Laue | Monochromatic | Quasi-Laue |
| Wavelength (A) | 0.4--3.45 | 0.7--2.89 | 0.8--4.0 | selectable | ~2--4 |
| Max Q (1/A) | ~17 | ~14 | ~10 | variable | variable |
| Best for | Small cells, H location | Diffuse scattering | Proteins, large cells | Extreme conditions | Macromolecules |

---

## Data Reduction Parameters

### max_q
Maximum momentum transfer (Q) in inverse Angstroms for peak finding and
integration. Peaks at Q > max_q are discarded. Higher values give more peaks
and finer resolution but increase computation time. Typical: 10--17 inverse Angstroms.

### num_peaks_to_find
Number of peaks requested from the FindPeaksMD algorithm. More peaks improve
UB matrix determination but increase processing time. Typical: 200--500.

### tolerance
Fraction of a reciprocal lattice unit used when indexing peaks to integer HKL
values. Peaks with fractional part > tolerance are rejected. Lower = stricter
indexing. Typical: 0.10--0.15. Start with 0.12 and decrease if too many
spurious peaks are indexed.

### predict_peaks
Boolean. When True, CrystalPilot uses the UB matrix to predict peak
positions and integrate at predicted locations (PredictPeaks + IntegrateEllipsoids).
This improves completeness by including weak peaks not found by FindPeaksMD.

### peak_radius
Radius (in Q, inverse Angstroms) of the ellipsoidal integration region around
each peak center. Must be < bkg_inner_radius. Typical: 0.11--0.13. If too
large, neighboring peaks will overlap; if too small, peak intensity is lost.

### bkg_inner_radius / bkg_outer_radius
Inner and outer radii of the background annulus surrounding each peak.
Must satisfy: peak_radius < bkg_inner_radius < bkg_outer_radius.
Background is estimated from the shell between inner and outer radius.
The gap between peak_radius and bkg_inner_radius should be small but nonzero
to avoid integrating the peak tails into the background.

### pred_min_dspacing / pred_max_dspacing
D-spacing range (A) for predicted peaks. Sets the resolution cutoff for
PredictPeaks. Typical: 0.5--11 A.

### pred_min_wavelength / pred_max_wavelength
Wavelength range (A) for predicted peaks. Should match the instrument's
usable bandwidth. Typical: 0.4--3.5 A for TOPAZ; 0.7--2.9 A for CORELLI;
0.8--4.0 A for MANDI.

### abc_min / abc_max
Shortest and longest lattice parameters (in A) used as search constraints
for the FindUBUsingFFT algorithm. These bounds help the algorithm converge
faster. Default: abc_min = 3 A, abc_max = 18 A. Adjust if your cell edges
fall outside this range.

### edge_pixels
Number of pixels at detector edges to exclude from peak finding. Peaks near
the edge may have unreliable intensities. Default: 0. Increase to 5--10 if
edge artifacts are seen.

### split_threshold
Threshold for splitting events between adjacent detectors. Default: 80.
Lower values split more aggressively (useful for tightly spaced detectors);
higher values keep more events in the primary detector.

---

## Anvred Correction Parameters

The Anvred (angle-resolved normalization) step corrects integrated intensities
for incident spectrum shape, detector efficiency, and absorption effects.

### spectra_filename
Path to the spectrum file for the current instrument cycle. This is a
measured spectrum (usually from vanadium) used to normalize peak intensities
across the wavelength band.

### norm_to_wavelength
Wavelength (A) to which spectra are normalized. Default: 1.0 A. All
intensities are scaled as if measured at this wavelength.

### scale_factor
Multiplicative factor applied to all Fsquared and sigma(Fsquared) values.
Default: 0.05 for TOPAZ. Adjust if output intensity scale needs matching
to other datasets.

### min_intensity
Minimum integrated intensity cutoff. Peaks with integrated intensity below
this value are discarded. Default: 10. Increase to remove weak/unreliable
peaks; decrease to retain more data at the cost of noise.

### min_isigi
Minimum I/sigma(I) ratio. Peaks with I/sigI below this threshold are
rejected. Default: 2.0. Higher values give more reliable data but fewer
reflections.

### z_score
Statistical outlier test. Peaks with |I - mean(I)| / sigma(I) greater than
this value are flagged as outliers and excluded. Default: 4.0. Set to a
negative value to disable this test entirely. Use 3--5 for standard data;
lower values are stricter.

### border_pixels (reject_border_width)
Width (in pixels) of the detector border region in which peaks are rejected.
Default: 18. Peaks near detector edges often have unreliable background
estimation.

### min_dspacing / max_dspacing
D-spacing range (A) for the Anvred normalization. Peaks outside this range
are excluded. This is separate from the predicted d-spacing range.

### min_wavelength / max_wavelength
Wavelength range (A) for Anvred. Should match the instrument bandwidth.

### starting_batch_number
Starting batch number for HKL output files. Default: 1. Used when combining
multiple runs into a single dataset.

---

## Satellite Peak Configuration

For **incommensurate (modulated) structures**, CrystalPilot supports satellite
peak indexing. Satellite peaks appear at positions offset from the main Bragg
peaks by a modulation vector q, indexed as h+m*q_1+n*q_2+p*q_3.

### When to enable satellite peak indexing
- The sample shows extra peaks that cannot be indexed with the basic unit cell
- The material has a known incommensurate or commensurate superstructure
- Charge density waves, spin density waves, or orbital ordering is expected

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| index_satellite_peaks | boolean | Enable satellite peak indexing | false |
| mod_vec_1 | array | First modulation vector (dh, dk, dl) in reciprocal lattice units | 0, 0, 0 |
| mod_vec_2 | array | Second modulation vector | 0, 0, 0 |
| mod_vec_3 | array | Third modulation vector | 0, 0, 0 |
| max_order | integer | Maximum order of satellite reflections to index (0 = main peaks only) | 0 |
| cross_terms | boolean | Include cross-term satellites (mixed orders from multiple vectors) | false |
| tolerance_satellite | float | Tolerance for satellite peak indexing (usually tighter than main peaks) | 0.08 |
| sat_peak_radius | float | Integration radius for satellite peaks (inverse Angstroms) | 0.08 |
| sat_peak_region_radius | float | Region radius for satellite peaks | 0.11 |
| sat_peak_inner_radius | float | Background inner radius for satellite peaks | 0.09 |
| sat_peak_outer_radius | float | Background outer radius for satellite peaks | 0.10 |

### Workflow for satellite peaks
1. First collect and reduce data with satellite indexing disabled.
2. Examine the diffraction pattern for extra peaks not indexed by the
   main unit cell.
3. Determine the modulation vector(s) from the offset positions.
4. Enable satellite indexing and enter the modulation vectors.
5. Set max_order to 1 initially, then increase if higher-order satellites
   are visible.
6. Use a tighter tolerance for satellites (0.08) than main peaks (0.12)
   since satellite positions are less precisely known.

---

## Angle Plan

The angle plan is a table of goniometer settings for a series of measurement
runs. Each row is one run with these fields:

| Field | Description |
|-------|-------------|
| phi | Phi goniometer angle (degrees) |
| omega | Omega goniometer angle (degrees) |
| title | Human-readable label for the run |
| comment | Optional comment |
| wait_for | Condition to wait for before counting: `PCharge` (proton charge) or `Time` |
| value | Amount of PCharge (microAh) or time (s) to collect |
| or_time | Maximum time (s) override; 0 = no override |

**PCharge** (proton charge, microAh) is the preferred way to normalize runs at
a spallation source because it tracks the actual number of neutrons delivered
to the sample, correcting for accelerator variations.

### Angle Plan Optimization

An optimal angle plan distributes phi/omega settings to maximize reciprocal
space coverage. Key considerations:
- At least two orientations are typically needed; three or more
  give a complete data set for structural analysis.
- Rotate in steps of approximately 20--30 degrees in phi or omega to
  cover different regions of reciprocal space.
- For high-symmetry crystals (cubic, tetragonal), fewer orientations may
  suffice due to symmetry-equivalent reflections.
- For low-symmetry crystals (triclinic, monoclinic), more orientations are
  needed for completeness.
- Check coverage statistics after each run; add supplementary orientations
  to fill gaps.

### NeuXtalViz (NXV) Integration — Detailed Workflow

CrystalPilot integrates with NeuXtalViz (NXV) for interactive 3D reciprocal-
space coverage visualization and strategy editing. The integration uses a
file-based CSV exchange: CrystalPilot exports the current angle plan, NXV
opens it for visual editing, and when NXV closes the edited plan is
automatically reimported.

#### Step-by-step workflow

1. **(Optional) Initialize Strategy**
   Click **Initialize Strategy** on the Experiment Steering tab. This runs
   the built-in angle plan optimizer which populates the strategy table with
   an initial set of goniometer orientations based on the sample symmetry
   and instrument geometry. You can skip this if you want to build a plan
   from scratch inside NXV.

2. **Launch NXV via "Show Coverage"**
   Click **Show Coverage**. CrystalPilot will:
   - Export the current angle plan table to a temporary CSV file
     (`/tmp/crystalpilot_nxv_plan.csv`) in NXV-compatible format with
     columns: `BL12:Mot:goniokm:omega`, `BL12:Mot:goniokm:chi`,
     `BL12:Mot:goniokm:phi`, `comment`
   - Launch NeuXtalViz as an external process, passing:
     - `--initialize-planner <UB.mat>` (if a UB matrix file is configured
       in the IPTS Info tab) — loads the UB and runs initial coverage
       optimization
     - `--open-plan <csv>` — loads the exported strategy into NXV's planner
       table
   - The CrystalPilot UI remains responsive while NXV is open.

3. **Edit strategy visually inside NXV**
   Inside NXV's Experiment Planner:
   - View the 3D reciprocal-space coverage for the current orientations
   - Add, remove, or modify orientations
   - Use NXV's built-in optimizer to improve coverage for specific peaks
   - Toggle orientations on/off using the "Use" checkbox
   - When finished, simply **close the NXV window** — the edited plan is
     automatically saved back to the same CSV file.

4. **Automatic reimport**
   When NXV closes, CrystalPilot detects the process exit and automatically:
   - Reads the updated CSV file
   - Replaces the angle plan table with the edited orientations
   - Fills in default EIC parameters (Wait For = "PCharge", Value = 10)
   - Refreshes the UI
   No manual file import is needed.

5. **(Optional) Further manual edits**
   After reimport, you can still edit individual runs in the CrystalPilot
   table: click the pencil icon to modify angles, or use "Add a Run" to
   append additional orientations.

6. **Submit through EIC**
   When the strategy is finalized, authenticate with the EIC token and click
   **Submit through EIC** to send the plan to the instrument control system.

7. **Auto-steering (during data collection)**
   While runs execute, CrystalPilot's live data monitoring can automatically
   stop a run when the data quality threshold is reached:
   - **By Uncertainty**: stops when Poisson uncertainty drops below the
     configured threshold
   - **By SNR**: stops when signal-to-noise ratio exceeds the threshold
   - **No Auto Stop**: manual stop only via "Manual Stop Run" button
   The auto-stop strategy and threshold are configured at the bottom of the
   Experiment Steering tab.

#### CSV format reference

The exchange CSV uses NXV's native motor column names:

```csv
BL12:Mot:goniokm:omega,BL12:Mot:goniokm:chi,BL12:Mot:goniokm:phi,comment
0.0,135.0,0.0,orientation_1
10.0,135.0,45.0,orientation_2
```

- The `comment` column maps to CrystalPilot's `title` field
- EIC-specific columns (Wait For, Value, Or Time) are not in the CSV; they
  are filled with defaults on reimport and can be edited in the table

#### Troubleshooting

- **NXV does not launch**: Check that the conda environment `nxvnew` exists
  and that `~/.miniforge/bin/activate` is the correct activate script path.
- **Plan not reimported**: Verify that NXV was closed normally (not killed).
  The auto-save runs in the window close event handler.
- **Empty table after reimport**: The CSV may be empty. Check
  `/tmp/crystalpilot_nxv_plan.csv` contents.
- **UB not loaded in NXV**: Ensure the UB file path in IPTS Info tab points
  to a valid `.mat` file.

---

## IPTS (Instrument Proposal Tracking System)

IPTS is ORNL's experiment proposal and data management system. Each approved
experiment is assigned an **IPTS number** (e.g., IPTS-35078). This number
is used to:
- Locate the raw data directory on the facility file system
  (e.g. /SNS/TOPAZ/IPTS-35078/nexus/)
- Identify the calibration files for that run cycle
- Tag output reduction files for the proposal
- Construct the export folder path
  (e.g. /SNS/TOPAZ/IPTS-35078/shared/experiment_name/)

In CrystalPilot, enter the IPTS number in the IPTS Info tab. The system uses
it to construct the data and output paths.

---

## EIC Control

EIC (Experiment Information Collection) is the ORNL system for registering
experiment metadata and submitting scan plans. CrystalPilot's EIC Control
functionality allows you to:
- Authenticate using a facility token
- Set simulation mode for testing (no actual motor movement)
- Submit the angle plan for automated execution on the instrument
- Monitor submission status and scan progress
- Configure auto-stop strategies (by uncertainty or signal-to-noise ratio)

The EIC handles the communication between CrystalPilot and the instrument
control system, translating the angle plan into motor commands.

---

## Live Data Processing

CrystalPilot supports real-time data monitoring through the Live Data
Processing tab. This integrates with Mantid's live data streaming
capabilities.

### How live data works
1. Press Auto Update to begin streaming live reduction results.
2. The system connects to the instrument's event stream and accumulates
   neutron events in real time.
3. As data accumulates, peaks are found, indexed, and integrated continuously.
4. The live display shows the current diffraction pattern and peak statistics.
5. Use this to confirm the experiment is running correctly before committing
   to long counting times.

### What to monitor during live data
- Peak count: are peaks appearing at expected positions?
- Indexing rate: what fraction of found peaks are successfully indexed?
- Unit cell parameters: do they match expected values?
- Background levels: is the signal-to-noise acceptable?
- Coverage: are new reciprocal space regions being filled?

### Flux and Solid Angle Corrections

For quantitative intensity analysis during live monitoring:
- **SAFile** (Solid Angle File): vanadium file for solid angle correction
  for this run cycle. Used for plotting only.
- **FluxFile** (Flux File): vanadium file for flux normalization for this
  run cycle. Used for plotting only.

---

## Mantid Algorithms Used in CrystalPilot

CrystalPilot drives the following Mantid algorithms for live and offline
data reduction:

- **LoadLiveData / StartLiveData / MonitorLiveData**: stream live neutron events
  from the instrument as they arrive
- **ConvertToMD**: convert event workspace to MD (multi-dimensional) workspace
  in Q-space for peak finding
- **FindPeaksMD**: locate Bragg peaks in the MD workspace; controlled by
  num_peaks_to_find and max_q parameters
- **IndexPeaks**: assign integer (H,K,L) indices to found peaks using UB matrix;
  controlled by tolerance parameter
- **FindUBUsingFFT / FindUBUsingLatticeParameters**: determine the UB matrix
  from a set of indexed peaks; abc_min and abc_max constrain the search
- **PredictPeaks**: generate predicted peak locations from the UB matrix;
  controlled by pred_min/max_dspacing and pred_min/max_wavelength
- **IntegrateEllipsoids**: integrate peak intensities using 3D ellipsoidal
  regions in the raw event data; peak_radius, bkg_inner_radius,
  bkg_outer_radius control the integration geometry
- **AnvredCorrection**: apply angle-resolved normalization and absorption
  corrections using the spectra file and sample parameters

---

## Common Workflow

1. Open CrystalPilot and navigate to the **IPTS Info** tab.
2. Enter your IPTS number, sample name, and chemical formula.
3. Set the crystal system, centering, and point group (call `refresh_schema`
   after changing crystal system to update the available options).
4. Enter known lattice parameters (a, b, c, alpha, beta, gamma) if available.
5. Go to the **Experiment Steering** (Angle Plan) tab; add runs with `append_run`.
6. Set data reduction parameters, or apply a preset
   matching your instrument (`topaz_standard`, `corelli_standard`,
   `mandi_standard`).
7. Navigate to **Live Data Processing** and click Auto Update to start
   live reduction.

---

## Troubleshooting

### Too few peaks indexed
- Decrease `tolerance` (stricter but fewer spurious assignments)
- Increase `num_peaks_to_find`
- Check that the lattice parameters match the sample
- Verify the crystal system and centering are correct
- Ensure abc_min and abc_max bracket the actual cell edges

### UB matrix cannot be determined
- Need at least ~25 well-indexed peaks; increase `num_peaks_to_find`
- Ensure there is enough Q coverage -- check that max_q and wavelength
  ranges are appropriate for the instrument
- Try widening abc_min/abc_max bounds if the unit cell is unusual
- Check for a twinned crystal or multiple grains

### No peaks found
- Check that the sample is correctly centered on the beam
- Verify the instrument is correctly set in CrystalPilot
- Ensure the wavelength range matches the instrument settings
- Reduce edge_pixels if too many peaks are near detector edges
- Increase num_peaks_to_find

### Background is too high
- Reduce `bkg_outer_radius` to exclude diffuse scattering
- Check for preferred orientation or multiple grains in the crystal
- Increase `min_intensity` and `min_isigi` thresholds
- Consider using CORELLI's energy discrimination if available

### Peak intensities seem wrong
- Verify the spectra file matches the current instrument cycle
- Check that scale_factor is appropriate (default 0.05 for TOPAZ)
- Ensure min_wavelength and max_wavelength match the instrument bandwidth
- Review z_score setting -- set negative to disable outlier rejection
  if too many peaks are being excluded

### Satellite peaks not indexing
- Verify the modulation vectors are entered correctly
- Start with max_order = 1 before trying higher orders
- Use a tolerance_satellite of 0.08 or smaller
- Ensure the main Bragg peaks are well indexed first
- Check that index_satellite_peaks is set to True

---

## Parameter Reference: Sample Information

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| exp_name | string | Used to create a directory in the shared folder under the IPTS directory | test |
| instrument | enum | Instrument name: TOPAZ, MANDI, or CORELLI | TOPAZ |
| molecular_formula | string | Molecular formula, e.g. for oxalic acid dihydrate: C2 O6 H6 | |
| Z | number | Number of formula units in the unit cell | 1.0 |
| unit_cell_volume | number | Unit cell volume in Angstroms cubed | |
| sample_radius | number | Crystal radius in mm, used to calculate linear absorption coefficients | 0.0 |
| crystalsystem | enum | Crystal system (Triclinic, Monoclinic, Orthorhombic, Tetragonal, Trigonal/Rhombohedral, Trigonal/Hexagonal, Hexagonal, Cubic) | Cubic |
| centering | string | Bravais lattice centering for the point group (P, I, F, A, B, C, R, Robv, Rrev) | P |
| point_group | string | Crystallographic point group | m-3 |

---

## Parameter Reference: Reduction Input

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| ipts_number | string | Proposal number for the experiment | 35036 |
| cal_filename | string | Calibration file for the current instrument cycle | |
| run_nums | string | Range of run numbers, comma-separated or first:last | |
| max_q | number | Maximum Q for peak integration (inverse Angstroms) | 17.0 |
| split_threshold | integer | Split threshold for event filtering | 80 |
| edge_pixels | integer | Detector edge exclusion width (pixels) | 0 |
| subtract_bkg | boolean | Enable background subtraction | false |
| background_filename | string | NXS file for background measurement | |
| read_ub | boolean | Read UB matrix from file instead of determining it | false |
| UBFileName | string | Path to UB matrix file | |
| data_directory | string | Directory containing the nexus data files | |

---

## Parameter Reference: Peak Input

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| num_peaks_to_find | integer | Peaks to find per run for UB matrix determination | 500 |
| abc_min | number | Shortest cell edge in Niggli reduced cell (A) | 3.0 |
| abc_max | number | Longest lattice parameter (A) | 18.0 |
| tolerance | number | Tolerance for indexing peaks to integer HKL | 0.12 |
| predict_peaks | boolean | Enable prediction of peaks from UB matrix | true |
| pred_min_dspacing | number | Minimum d-spacing for predicted peaks (A) | 0.499 |
| pred_max_dspacing | number | Maximum d-spacing for predicted peaks (A) | 11.0 |
| pred_min_wavelength | number | Minimum wavelength for predicted peaks (A) | 0.4 |
| pred_max_wavelength | number | Maximum wavelength for predicted peaks (A) | 3.45 |
| peak_radius | number | Longest axis radius for ellipse integration (inverse Angstroms) | 0.11 |
| bkg_inner_radius | number | Inner radius of background shell (inverse Angstroms) | 0.115 |
| bkg_outer_radius | number | Outer radius of background shell (inverse Angstroms) | 0.14 |

---

## Parameter Reference: Anvred Input

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| spectra_filename | string | Spectrum file for the current instrument cycle | |
| norm_to_wavelength | number | Normalize spectra to this wavelength (A) | 1.0 |
| scale_factor | number | Multiply Fsquared and sigma(Fsquared) by this factor | 0.05 |
| min_intensity | number | Minimum integrated intensity cutoff | 10 |
| min_isigi | number | Minimum I/sigma(I) ratio | 2.0 |
| z_score | number | Maximum |I - mean(I)|/sigma(I) for outlier test; negative disables | 4.0 |
| border_pixels | integer | Width of border where peaks are rejected | 18 |
| min_dspacing | number | Minimum d-spacing (A) | 0.5 |
| max_dspacing | number | Maximum d-spacing (A) | 30.0 |
| min_wavelength | number | Minimum wavelength (A) | 0.4 |
| max_wavelength | number | Maximum wavelength (A) | 3.5 |
| starting_batch_number | integer | Starting batch number for output | 1 |

---

## Parameter Reference: Satellite Peaks

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| index_satellite_peaks | boolean | Enable satellite peak indexing | false |
| mod_vec_1 | array | First modulation vector (dh, dk, dl) | 0, 0, 0 |
| mod_vec_2 | array | Second modulation vector | 0, 0, 0 |
| mod_vec_3 | array | Third modulation vector | 0, 0, 0 |
| max_order | integer | Maximum satellite order | 0 |
| cross_terms | boolean | Include cross-term satellites | false |
| tolerance_satellite | number | Tolerance for satellite peak indexing | 0.08 |
| sat_peak_radius | number | Integration radius for satellite peaks | 0.08 |
| sat_peak_region_radius | number | Region radius for satellite peaks | 0.11 |
| sat_peak_inner_radius | number | Background inner radius for satellite peaks | 0.09 |
| sat_peak_outer_radius | number | Background outer radius for satellite peaks | 0.10 |

---

## Parameter Reference: Plotting and Visualization

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| SAFile | string | Vanadium solid angle file for this cycle (for plotting) | |
| FluxFile | string | Vanadium flux file for this cycle (for plotting) | |
