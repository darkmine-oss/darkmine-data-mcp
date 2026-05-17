# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

"""Validation helpers for MCP tool inputs."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .errors import DarkmineValidationError

BBOX_MIN_LENGTH = 4
MAX_LIMIT = 10000
TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

CONFIG_TABLES = {
    "cfg_analytematchingtable",
    "cfg_customdatum",
    "cfg_customgrid",
    "cfg_datum",
    "cfg_datumlookup",
    "cfg_grid",
    "cfg_gridlookup",
    "cfg_lookupgeochemistryunitofmeasure",
    "cfg_lookupholetype",
    "cfg_lookupnoncompliancereason",
    "cfg_lookupsurfacesampleobservationtype",
    "cfg_lookupsurfacesampletype",
    "dbo_clbody",
    "dbo_surfacesampleobservationtype",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BboxMixin(BaseModel):
    bbox: list[float] | None = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value: list[float] | None) -> list[float] | None:
        if value is None:
            return value
        if len(value) != BBOX_MIN_LENGTH:
            raise ValueError("bbox must contain [min_lon, min_lat, max_lon, max_lat].")
        min_lon, min_lat, max_lon, max_lat = value
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("bbox longitudes must be between -180 and 180.")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("bbox latitudes must be between -90 and 90.")
        if min_lon >= max_lon:
            raise ValueError("bbox min_lon must be less than max_lon.")
        if min_lat >= max_lat:
            raise ValueError("bbox min_lat must be less than max_lat.")
        return value


class PaginationMixin(BaseModel):
    limit: int = Field(default=1000, ge=1)
    offset: int = Field(default=0, ge=0)


class QueryRowsInput(StrictModel, BboxMixin, PaginationMixin):
    table_name: str
    collar_id: int | None = None
    hole_id: str | None = None
    company_hole_id: str | None = None
    dataset: str | None = None
    surface_sample_id: int | None = None
    sample_id: int | None = None
    sample_identifier: str | None = None
    company_sample_id: str | None = None
    sample_dataset: str | None = None
    parent_id: int | None = None
    anumber: int | None = None
    output: Literal["json", "geojson"] = "json"

    @field_validator("table_name")
    @classmethod
    def validate_table_name(cls, value: str) -> str:
        if not TABLE_NAME_RE.fullmatch(value):
            raise ValueError("table_name must be a simple GSWA table identifier.")
        return value

    @model_validator(mode="after")
    def require_selector_for_non_config(self) -> "QueryRowsInput":
        if self.table_name in CONFIG_TABLES:
            return self
        if not has_any_selector(self):
            raise ValueError("At least one filter is required for non-lookup tables.")
        return self


class DescribeTableInput(StrictModel):
    table_name: str

    _validate_table_name = field_validator("table_name")(QueryRowsInput.validate_table_name)


class DrillholeSelector(StrictModel, BboxMixin, PaginationMixin):
    collar_id: int | None = None
    hole_id: str | None = None
    company_hole_id: str | None = None
    dataset: str | None = None
    anumber: int | None = None

    @model_validator(mode="after")
    def require_selector(self) -> "DrillholeSelector":
        if not has_any_selector(self):
            raise ValueError("At least one drillhole selector is required.")
        return self


class DrillholeLocationsInput(DrillholeSelector):
    output: Literal["json", "geojson"] = "json"


class DrillholeFamilyInput(StrictModel):
    collar_id: int | None = None
    hole_id: str | None = None
    company_hole_id: str | None = None
    dataset: str | None = None
    anumber: int | None = None
    include_mrt: bool = False
    limit_per_table: int = Field(default=1000, ge=1)

    @model_validator(mode="after")
    def require_selector(self) -> "DrillholeFamilyInput":
        if not has_any_selector(self):
            raise ValueError("At least one drillhole selector is required.")
        return self


class SurfaceSampleSelector(StrictModel, BboxMixin, PaginationMixin):
    surface_sample_id: int | None = None
    sample_identifier: str | None = None
    company_sample_id: str | None = None
    sample_dataset: str | None = None
    anumber: int | None = None

    @model_validator(mode="after")
    def require_selector(self) -> "SurfaceSampleSelector":
        if not has_any_selector(self):
            raise ValueError("At least one surface-sample selector is required.")
        return self


class SurfaceSampleFamilyInput(StrictModel):
    surface_sample_id: int | None = None
    sample_identifier: str | None = None
    company_sample_id: str | None = None
    sample_dataset: str | None = None
    anumber: int | None = None
    include_mrt: bool = False
    limit_per_table: int = Field(default=1000, ge=1)

    @model_validator(mode="after")
    def require_selector(self) -> "SurfaceSampleFamilyInput":
        if not has_any_selector(self):
            raise ValueError("At least one surface-sample selector is required.")
        return self


class DrillholeGeochemistryInput(DrillholeSelector):
    pass


class SurfaceGeochemistryInput(SurfaceSampleSelector):
    pass


def has_any_selector(value: Any) -> bool:
    selector_names = (
        "bbox",
        "collar_id",
        "hole_id",
        "company_hole_id",
        "dataset",
        "surface_sample_id",
        "sample_id",
        "sample_identifier",
        "company_sample_id",
        "sample_dataset",
        "parent_id",
        "anumber",
    )
    return any(getattr(value, name, None) is not None for name in selector_names)


def clamp_limit(limit: int, max_records: int) -> int:
    if limit < 1:
        raise DarkmineValidationError("limit must be at least 1.")
    if limit > max_records:
        raise DarkmineValidationError(f"limit must be no greater than {max_records}.")
    return limit


def bbox_to_api_params(bbox: list[float]) -> dict[str, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
    }


def clean_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
