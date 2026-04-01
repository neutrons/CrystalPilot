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
- **d-spacing**: interplanar spacing in Angstroms (Å); related to scattering
  angle by Bragg's law: nλ = 2d·sin(θ)
- **Q (momentum transfer)**: Q = 4π·sin(θ)/λ = 2π/d; measured in Å⁻¹
- **Wavelength (λ)**: neutron wavelength in Å; at SNS instruments the full
  white-beam polychromatic spectrum is used (Laue method)
- **UB matrix**: 3×3 matrix relating crystal lattice vectors to laboratory
  coordinates; required for peak indexing and prediction

---

## Crystal Systems and Bravais Lattices

There are seven crystal systems defined by the metric symmetry of the unit cell:

| System | Constraints |
|--------|-------------|
| Cubic | a = b = c, α = β = γ = 90° |
| Tetragonal | a = b ≠ c, α = β = γ = 90° |
| Orthorhombic | a ≠ b ≠ c, α = β = γ = 90° |
| Monoclinic | a ≠ b ≠ c, α = γ = 90°, β ≠ 90° |
| Triclinic | a ≠ b ≠ c, α ≠ β ≠ γ ≠ 90° |
| Trigonal/Rhombohedral | a = b = c, α = β = γ ≠ 90° |
| Hexagonal | a = b ≠ c, α = β = 90°, γ = 120° |

Centering types (lattice centering):
- **P** (Primitive): lattice points at corners only
- **I** (Body-centered): additional point at cell center (a+b+c)/2
- **F** (Face-centered): additional points at all face centers
- **A, B, C** (Base-centered): additional point on one pair of faces
- **R** (Rhombohedral): for trigonal/hexagonal; obverse/reverse settings
- **H**: hexagonal primitive

The 14 Bravais lattices combine crystal system + centering. Centering imposes
systematic absences on the diffraction pattern.

---

## Point Groups, Space Groups, and Laue Classes

A **point group** describes the rotational symmetry of a crystal; there are
32 crystallographic point groups. The **space group** adds translation
symmetry (screw axes, glide planes); there are 230 space groups.

The **Laue class** (11 centrosymmetric point groups) is what is directly
observable in a diffraction experiment because the diffraction pattern always
has inversion symmetry (Friedel's law). For example:
- Crystal system Cubic, point group m3m → Laue class m3m
- Tetragonal, 4/mmm → Laue class 4/mmm

When setting up CrystalPilot, you first choose the **crystal system**, which
determines the list of valid **centering** options and **point groups**.
Call `refresh_schema` after changing the crystal system so the agent sees
the updated centering and point group lists.

---

## TOPAZ Instrument (SNS BL-12)

TOPAZ is a time-of-flight (TOF) single-crystal Laue diffractometer at the
Spallation Neutron Source. It uses the full white-beam polychromatic neutron
spectrum and a large array of flat panel detectors.

**Typical operating parameters:**
- Wavelength range: 0.4 – 3.45 Å
- Maximum Q: ~17 Å⁻¹ (atomic resolution, small unit cells)
- d-spacing range: 0.499 – 11.0 Å
- Peak finding: ~500 peaks recommended
- Peak integration radius: ~0.11
- Background inner/outer radius: ~0.115 / ~0.14
- Tolerance for indexing: 0.12

TOPAZ excels at high-resolution studies of materials with small-to-medium
unit cells. Its wide wavelength and Q coverage make it suitable for precise
atomic coordinate determination.

Standard preset: `topaz_standard` in CrystalPilot.

---

## CORELLI Instrument (SNS BL-9)

CORELLI is an elastic diffuse-scattering spectrometer and single-crystal
diffractometer using a statistical chopper system. It is optimized for
diffuse scattering and structural disorder studies but also used for standard
single-crystal work.

**Typical operating parameters:**
- Wavelength range: 0.7 – 2.89 Å
- Maximum Q: ~14 Å⁻¹
- d-spacing range: 0.5 – 10.0 Å
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
- Wavelength range: 0.8 – 4.0 Å
- Maximum Q: ~10 Å⁻¹
- d-spacing range: 0.7 – 7.0 Å
- Peak finding: ~200 peaks recommended
- Tolerance for indexing: 0.10

MANDI is the choice for biological macromolecules (proteins, nucleic acids),
large pharmaceutical molecules, and other systems with large unit cells.
Long wavelengths reduce background and improve contrast for hydrogen.

Standard preset: `mandi_standard` in CrystalPilot.

---

## Data Reduction Parameters

### max_q
Maximum momentum transfer (Q) in Å⁻¹ for peak finding and integration.
Peaks at Q > max_q are discarded. Higher values give more peaks and finer
resolution but increase computation time. Typical: 10–17 Å⁻¹.

### num_peaks_to_find
Number of peaks requested from the FindPeaksMD algorithm. More peaks improve
UB matrix determination but increase processing time. Typical: 200–500.

### tolerance
Fraction of a reciprocal lattice unit used when indexing peaks to integer HKL
values. Peaks with fractional part > tolerance are rejected. Lower = stricter
indexing. Typical: 0.10–0.15.

### predict_peaks
Boolean. When True, CrystalPilot uses the UB matrix to predict peak
positions and integrate at predicted locations (PredictPeaks + IntegrateEllipsoids).
This improves completeness by including weak peaks not found by FindPeaksMD.

### peak_radius
Radius (in Q, Å⁻¹) of the ellipsoidal integration region around each peak
center. Must be < bkg_inner_radius. Typical: 0.11–0.13.

### bkg_inner_radius / bkg_outer_radius
Inner and outer radii of the background annulus surrounding each peak.
Must satisfy: peak_radius < bkg_inner_radius < bkg_outer_radius.
Background is estimated from the shell between inner and outer radius.

### pred_min_dspacing / pred_max_dspacing
D-spacing range (Å) for predicted peaks. Sets the resolution cutoff for
PredictPeaks. Typical: 0.5–11 Å.

### pred_min_wavelength / pred_max_wavelength
Wavelength range (Å) for predicted peaks. Should match the instrument's
usable bandwidth. Typical: 0.4–3.5 Å for TOPAZ; 0.7–2.9 Å for CORELLI;
0.8–4.0 Å for MANDI.

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
| value | Amount of PCharge (μAh) or time (s) to collect |
| or_time | Maximum time (s) override; 0 = no override |

**PCharge** (proton charge, μAh) is the preferred way to normalize runs at
a spallation source because it tracks the actual number of neutrons delivered
to the sample, correcting for accelerator variations.

An optimal angle plan distributes phi/omega settings to maximize reciprocal
space coverage. At least two orientations are typically needed; three or more
give a complete data set for structural analysis.

---

## IPTS (Instrument Proposal Tracking System)

IPTS is ORNL's experiment proposal and data management system. Each approved
experiment is assigned an **IPTS number** (e.g., IPTS-35078). This number
is used to:
- Locate the raw data directory on the facility file system
- Identify the calibration files for that run cycle
- Tag output reduction files for the proposal

In CrystalPilot, enter the IPTS number in the IPTS Info tab. The system uses
it to construct the data and output paths.

---

## EIC Control

EIC (Experiment Information Collection) is the ORNL system for registering
experiment metadata. CrystalPilot's EIC Control tab allows you to fill in
sample information, PI details, and safety information required before a run
can start. This information is submitted to the facility's EIC database.

---

## Mantid Algorithms Used in CrystalPilot

CrystalPilot drives the following Mantid algorithms for live and offline
data reduction:

- **LoadLiveData / StartLiveData / StopLiveData**: stream live neutron events
  from the instrument as they arrive
- **ConvertToMD**: convert event workspace to MD (multi-dimensional) workspace
  in Q-space for peak finding
- **FindPeaksMD**: locate Bragg peaks in the MD workspace
- **IndexPeaks**: assign integer (H,K,L) indices to found peaks using UB matrix
- **FindUBUsingFFT / FindUBUsingLatticeParameters**: determine the UB matrix
- **PredictPeaks**: generate predicted peak locations from the UB matrix
- **IntegrateEllipsoids**: integrate peak intensities using 3D ellipsoidal
  regions in the raw event data

---

## Common Workflow

1. Open CrystalPilot and navigate to the **IPTS Info** tab.
2. Enter your IPTS number, sample name, and chemical formula.
3. Set the crystal system, centering, and point group (call `refresh_schema`
   after changing crystal system to update the available options).
4. Enter known lattice parameters (a, b, c, α, β, γ) if available.
5. Go to the **Experiment Steering** (Angle Plan) tab; add runs with `append_run`.
6. Set data reduction parameters in the reduction tab, or apply a preset
   matching your instrument (`topaz_standard`, `corelli_standard`,
   `mandi_standard`).
7. Navigate to **Live Data Processing** and click Auto Update to start
   live reduction.

---

## Troubleshooting

### "Too few peaks indexed"
- Decrease `tolerance` (stricter but fewer spurious assignments)
- Increase `num_peaks_to_find`
- Check that the lattice parameters match the sample
- Verify the crystal system and centering are correct

### "UB matrix cannot be determined"
- Need at least ~25 well-indexed peaks; increase `num_peaks_to_find`
- Ensure there is enough Q coverage — check that max_q and wavelength
  ranges are appropriate for the instrument

### "No peaks found"
- Check that the sample is correctly centered on the beam
- Verify the instrument is correctly set in CrystalPilot
- Ensure the wavelength range matches the instrument settings

### Background is too high
- Reduce `bkg_outer_radius` to exclude diffuse scattering
- Check for preferred orientation or multiple grains in the crystal

---

## Parameter Reference: Sample Information

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| experiment_name | string | Used to create a directory in the shared folder under the IPTS directory | test |
| instrument_name | enum | Instrument name: TOPAZ, MANDI, or CORELLI | TOPAZ |
| molecular_formula | string | Molecular formula, e.g. for oxalic acid dihydrate: C2 O6 H6 | |
| Z | number | Number of formula units in the unit cell | 1.0 |
| unit_cell_volume | number | Unit cell volume in Angstroms cubed (A^3) | |
| sample_radius | number | Crystal radius in mm, used to calculate linear absorption coefficients | 0.0 |
| crystal_system | enum | Crystal system (Triclinic, Monoclinic, Orthorhombic, Tetragonal, Trigonal/Rhombohedral, Trigonal/Hexagonal, Hexagonal, Cubic) | Triclinic |
| centering | string | Bravais lattice centering for the point group (P, I, F, A, B, C, R, H) | |
| point_group | string | Crystallographic point group | |

---

## Parameter Reference: Reduction Input

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| ipts_number | string | Proposal number for the experiment | 12345 |
| calibration_file | string | Calibration file for the current instrument cycle | |
| run_nums | string | Range of run numbers, first:last (e.g. 32751:32758) | |
| maxq | number | Q limits for peak integration (A^-1) | 17.0 |
| split_threshold | integer | Split threshold for event filtering | 80 |
| export_folder | string | Output directory for reduced data files | |
| background_file | string | NXS file for background measurement of the current cycle | NONE |
| ub_filename | string | Optional UB matrix file | NONE |
| min_dspacing | number | Minimum d-spacing (A) or Q cutoff | 0.5 |
| data_directory | string | Directory containing the nexus data files | |

---

## Parameter Reference: Peak Input

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| num_peaks_to_find | integer | Peaks to find per run for UB matrix determination | 500 |
| abc_min | number | Shorter than shortest cell edge in the Niggli reduced cell (A) | 3.0 |
| abc_max | number | Longest lattice parameter (A) | 18.0 |
| tolerance | number | Tolerance for indexing peaks to integer HKL | 0.12 |
| num_borderCh | integer | Width of border region where peaks are rejected | 18 |
| predict_peaks | boolean | Enable prediction of peaks from UB matrix | false |
| min_pred_dspacing | number | Minimum d-spacing for predicted peaks (A) | 0.499 |
| max_pred_dspacing | number | Maximum d-spacing for predicted peaks (A) | 11.0 |
| min_pred_wl | number | Minimum wavelength for predicted peaks (A) | 0.4 |
| max_pred_wl | number | Maximum wavelength for predicted peaks (A) | 3.45 |
| peak_radius | number | Longest axis radius for ellipse integration (A^-1) | 0.11 |
| bkg_inner_radius | number | Inner radius of background shell (A^-1) | 0.115 |
| bkg_outer_radius | number | Outer radius of background shell (A^-1) | 0.14 |

---

## Parameter Reference: Anvred Input

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| spectra_file | string | Spectrum file for the current instrument cycle | |
| normalize_to_wavelength | number | Normalize spectra to this wavelength (A) | 1.0 |
| scale_factor | number | Multiply FSQ and sig(FSQ) by this factor | 1.0 |
| min_intensity | number | Minimum integrated intensity cutoff | 1.0 |
| min_isig | number | Minimum I/sig(I) ratio | 1.0 |
| z_score | number | Maximum |I - <I>|/<sigI> ratio; negative disables test | 5.0 |
| min_wavelength | number | Minimum wavelength (A) | 0.4 |
| max_wavelength | number | Maximum wavelength (A) | 3.5 |
| min_dspacing | number | Minimum d-spacing (A) | 0.5 |
| reject_border_width | integer | Width of border where peaks are rejected | 18 |
| start_batch_number | integer | Starting batch number for output | 1 |
