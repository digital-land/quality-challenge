from dataclasses import dataclass
from typing import Literal


@dataclass
class BaseMetadata:
    lat: float
    lon: float
    img_size: list[int]
    type: str


@dataclass
class GoogleStaticMetadata(BaseMetadata):
    zoom: int
    scale: int
    type: Literal["static"] = "static"


@dataclass
class GoogleTilesMetadata(BaseMetadata):
    zoom: int
    type: Literal["tiles"] = "tiles"


@dataclass
class WMSMetadata(BaseMetadata):
    bbox: tuple[float, float, float, float]
    type: Literal["wms"] = "wms"
