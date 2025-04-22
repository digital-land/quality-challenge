from dataclasses import dataclass, field
from typing import Literal


@dataclass
class BaseMetadata:
    lat: float
    lon: float
    img_size: tuple[int, int]


@dataclass
class GoogleStaticMetadata(BaseMetadata):
    zoom: int
    scale: int
    type: Literal["static"] = field(default="static")


@dataclass
class GoogleTilesMetadata(BaseMetadata):
    zoom: int
    type: Literal["tiles"] = field(default="tiles")


@dataclass
class WMSMetadata(BaseMetadata):
    bbox: tuple[float, float, float, float]
    type: Literal["wms"] = field(default="wms")
