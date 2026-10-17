# Project Kairo — Working Notes
Repo: github.com/bl4dereaper/Project Kairo · Focus: DSLR/mirrorless camera support + streamlining


## System Overview
Purpose: enables scholars, curators, researchers with non-scientific backgrounds to analyze cultural heritage items (manuscripts, historical documents, etc.)
Output: ENVI spectral image cubes
Architecture

### Stack: Python 3.x + PyQt5 GUI
Layout under src/:
controllers/ — camera and LED abstraction
cube_creation/ — ENVI cube assembly
operations/ — image processing utilities
skeleton/ — UI assets, color-matching CSVs, Qt .ui files
Main entry point: src/main.py

### Existing Camera Support
Pixelink (pixilink_controller.py)
FLIR Blackfly (blackfly_controller.py, uses PySpin/Spinnaker SDK)
Baumer (baumer_controller.py)
Mock controller for hardware-free testing (camera_mock.py)


# Project Kairo
### New Feature: Converted Camera Support
Goal: full-spectrum converted bodies (Kolari-style) — Canon, Nikon, Fuji first
Platform: Linux/macOS confirmed (Windows deferred)
Backend decision: libgphoto2 via python-gphoto2 — one library covers all three vendors over PTP; avoids three separate SDK integrations
### Key design points:
Capture-to-RAM (skips SD card write + download handshake)
Config-tree caching (avoid expensive PTP traversals per shot)
RAW capture, linear Bayer extraction via rawpy/LibRaw (no demosaic, no WB, no gamma — preserves linear reflectance signal)
Exposure floats mapped to nearest discrete camera shutter speed

### Output Shape Decision — RESOLVED
Chosen: Three-plane Bayer (Option B) — per band, return (H, W, 3):
Plane 0 = Red Bayer sites, Plane 1 = Green (both diagonal greens averaged, ~2× SNR), Plane 2 = Blue
Rejected: mono-only (loses channel-specific pigment signatures), demosaiced RGB (destroys linearity), bracketing (slower, only if glare issues demand it later)
Rationale: preserves maximum information for future scholarship; channel ratios are diagnostically useful

### Calibration Context
Spectralon = PTFE diffuse reflectance standard, the "ruler for brightness"
Normalize per band: Reflectance_doc = (DN_doc / DN_Spectralon) × R_Spectralon
Needed item: calibrated Labsphere SRS-series standard (99% white, ~$400–700; optionally grayscale set 99/50/20/2% for sensor linearity) — not a Newport port plug like 819M-PP-SL-1.5

### Streamlining Roadmap (agreed order)
Externalized rig config — exposureArray → YAML RigConfig/BandSpec dataclasses; validation at load; retune_band_exposure() + save() for UI retuning; legacy shim for old controllers. rig_config.py drafted ✓
Exposure state pattern — ExposureMode enum (FIXED / TABLE / AUTO) unifying reset_exposure/save_exposure (next up)
Frame-buffer refactor — factor _grab_raw_frame() / _frame_to_ndarray() pattern into base class; SDK differences localized to subclasses

### Open Questions
LED channel mapping (led_id) co-located in rig config? — leaning yes (single source of truth)
RigConfig authoring: real per-rig YAML files to be written for each system
