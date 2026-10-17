"""
rig_config.py — Externalized capture-rig configuration for MISHA.

Replaces the hard-coded 16-element `exposureArray` in camera_interface.py
with a per-rig, human-editable YAML file. Each band declares its center
wavelength, exposure, and LED channel, so a new camera/filter/illumination
combination is a config change, never a code change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BandSpec:
    """
    One spectral band of a capture sequence.

    frozen=True: BandSpec instances are immutable so they can be shared
    freely across threads (UI thread + capture worker) without locks.
    """

    wavelength_nm: int            # center wavelength of the band
    exposure_s: float             # exposure time in seconds
    led_id: int                   # LED channel / index on the LED controller
    label: Optional[str] = None   # optional human-readable name, e.g. "UV-A"

    def __post_init__(self) -> None:
        if self.wavelength_nm <= 0:
            raise ValueError(
                f"wavelength must be positive, got {self.wavelength_nm}")
        if self.exposure_s <= 0:
            raise ValueError(
                f"exposure must be positive, got {self.exposure_s}")


@dataclass
class RigConfig:
    """
    Complete band specification for one MISHA rig.

    Load with RigConfig.load(path); the loader validates every band so
    bad configs fail loudly at startup, not mid-capture-sequence.
    """

    rig_name: str
    bands: List[BandSpec] = field(default_factory=list)

    # ------------------------------------------------------------ #
    #  I/O                                                          #
    # ------------------------------------------------------------ #

    @classmethod
    def load(cls, path) -> "RigConfig":
        """Read and validate a rig config from YAML."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Rig config not found: {path}")

        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        if not isinstance(raw, dict) or "bands" not in raw:
            raise ValueError(
                f"{path}: expected top-level 'rig_name' and 'bands' keys")

        bands = [BandSpec(**b) for b in raw["bands"]]
        if not bands:
            raise ValueError(f"{path}: config contains zero bands")

        config = cls(rig_name=raw.get("rig_name", path.stem), bands=bands)
        logger.info("Loaded rig '%s': %d bands, %.0f-%.0f nm",
                    config.rig_name, len(bands),
                    bands[0].wavelength_nm, bands[-1].wavelength_nm)
        return config

    def save(self, path) -> None:
        """Persist current config — used by the UI after exposure retuning."""
        payload = {
            "rig_name": self.rig_name,
            "bands": [asdict(b) for b in self.bands],
        }
        with Path(path).open("w", encoding="utf-8") as fh:
            yaml.safe_dump(payload, fh, sort_keys=False)

    # ------------------------------------------------------------ #
    #  Legacy compatibility shim                                     #
    # ------------------------------------------------------------ #

    @classmethod
    def from_legacy_exposure_array(cls, exposure_array) -> "RigConfig":
        """
        Build a RigConfig from the old hard-coded exposure array so existing
        code paths keep working during migration. Wavelengths and LED ids
        are sequential placeholders — good enough for capture, but a real
        config should be authored for each rig.
        """
        bands = [
            BandSpec(wavelength_nm=0, exposure_s=e, led_id=i)
            for i, e in enumerate(exposure_array)
        ]
        return cls(rig_name="legacy-compat", bands=bands)

    # ------------------------------------------------------------ #
    #  Sequence iteration                                            #
    # ------------------------------------------------------------ #

    def __iter__(self) -> Iterator[BandSpec]:
        return iter(self.bands)

    def __len__(self) -> int:
        return len(self.bands)

    def exposure_for(self, band_index: int) -> float:
        """Per-band exposure lookup with bounds checked once, up front."""
        if not 0 <= band_index < len(self.bands):
            raise IndexError(
                f"band index {band_index} out of range "
                f"(0..{len(self.bands) - 1})")
        return self.bands[band_index].exposure_s

    def retune_band_exposure(self, band_index: int, new_exposure_s: float) -> None:
        """Update one band's exposure (UI retuning entry point)."""
        old = self.bands[band_index]
        self.bands[band_index] = BandSpec(
            wavelength_nm=old.wavelength_nm,
            exposure_s=new_exposure_s,
            led_id=old.led_id,
            label=old.label,
        )
        logger.debug("Retuned band %d (%d nm): %.4fs -> %.4fs",
                     band_index, old.wavelength_nm,
                     old.exposure_s, new_exposure_s)
