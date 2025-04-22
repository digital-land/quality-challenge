from dataclasses import dataclass, field
from typing import Literal


@dataclass
class BaseMetadata:
    lat: float
    lon: float
    img_size: list[int]
    type: str = field(init=False)


@dataclass
class GoogleStaticMetadata(BaseMetadata):
    zoom: int
    scale: int
    type: Literal["static"] = field(init=False, default="static")


@dataclass
class GoogleTilesMetadata(BaseMetadata):
    zoom: int
    type: Literal["tiles"] = field(init=False, default="tiles")


@dataclass
class WMSMetadata(BaseMetadata):
    bbox: tuple[float, float, float, float]
    type: Literal["wms"] = field(init=False, default="wms")
