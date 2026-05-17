# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

"""FastMCP server tools for Darkmine raw GSWA data."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .client import DarkmineClient
from .config import DarkmineConfig, load_config
from .errors import DarkmineError, DarkmineValidationError
from .models import (
    DescribeTableInput,
    DrillholeFamilyInput,
    DrillholeGeochemistryInput,
    DrillholeLocationsInput,
    QueryRowsInput,
    SurfaceGeochemistryInput,
    SurfaceSampleFamilyInput,
    SurfaceSampleSelector,
    bbox_to_api_params,
    clamp_limit,
    clean_dict,
)

mcp = FastMCP("darkmine")

RAW_GSWA_PREFIX = "/v1/raw/gswa"


def _parse_model(model_cls: type[Any], values: dict[str, Any]) -> Any:
    try:
        return model_cls.model_validate(values)
    except ValidationError as exc:
        message = "; ".join(error["msg"] for error in exc.errors())
        raise DarkmineValidationError(message) from exc


def _selector_params(payload: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name in (
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
    ):
        value = getattr(payload, name, None)
        if value is not None:
            params[name] = value
    if getattr(payload, "bbox", None) is not None:
        params.update(bbox_to_api_params(payload.bbox))
    return params


def _query_rows_path(table_name: str) -> str:
    return f"{RAW_GSWA_PREFIX}/tables/{quote(table_name, safe='')}/rows"


def _schema_path(table_name: str) -> str:
    return f"{RAW_GSWA_PREFIX}/tables/{quote(table_name, safe='')}/schema"


async def _call_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    config = load_config()
    async with DarkmineClient(config) as client:
        return await client.get(path, params=clean_dict(params or {}))


async def _query_table(table_name: str, params: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    if "limit" in params:
        params["limit"] = clamp_limit(int(params["limit"]), config.max_records)
    if "limit_per_table" in params:
        params["limit_per_table"] = clamp_limit(int(params["limit_per_table"]), config.max_records)
    async with DarkmineClient(config) as client:
        return await client.get(_query_rows_path(table_name), params=clean_dict(params))


@mcp.tool()
async def gswa_list_tables() -> dict[str, Any]:
    """List raw GSWA tables and the filters each table supports."""
    return await _call_get(f"{RAW_GSWA_PREFIX}/tables")


@mcp.tool()
async def gswa_describe_table(table_name: str) -> dict[str, Any]:
    """Return schema, columns, relationships, and supported filters for a raw GSWA table."""
    payload = _parse_model(DescribeTableInput, {"table_name": table_name})
    return await _call_get(_schema_path(payload.table_name))


@mcp.tool()
async def gswa_query_table(
    table_name: str,
    collar_id: int | None = None,
    hole_id: str | None = None,
    company_hole_id: str | None = None,
    dataset: str | None = None,
    surface_sample_id: int | None = None,
    sample_id: int | None = None,
    sample_identifier: str | None = None,
    company_sample_id: str | None = None,
    sample_dataset: str | None = None,
    parent_id: int | None = None,
    anumber: int | None = None,
    bbox: list[float] | None = None,
    limit: int = 1000,
    offset: int = 0,
    output: str = "json",
) -> dict[str, Any]:
    """Query a raw GSWA table with bounded, explicit filters. No arbitrary SQL is accepted."""
    config = load_config()
    payload = _parse_model(
        QueryRowsInput,
        {
            "table_name": table_name,
            "collar_id": collar_id,
            "hole_id": hole_id,
            "company_hole_id": company_hole_id,
            "dataset": dataset,
            "surface_sample_id": surface_sample_id,
            "sample_id": sample_id,
            "sample_identifier": sample_identifier,
            "company_sample_id": company_sample_id,
            "sample_dataset": sample_dataset,
            "parent_id": parent_id,
            "anumber": anumber,
            "bbox": bbox,
            "limit": limit,
            "offset": offset,
            "output": output,
        },
    )
    params = _selector_params(payload)
    params.update(
        {
            "limit": clamp_limit(payload.limit, config.max_records),
            "offset": payload.offset,
            "output": payload.output,
        }
    )
    async with DarkmineClient(config) as client:
        return await client.get(_query_rows_path(payload.table_name), params=clean_dict(params))


@mcp.tool()
async def gswa_find_drillholes(
    bbox: list[float] | None = None,
    collar_id: int | None = None,
    hole_id: str | None = None,
    company_hole_id: str | None = None,
    dataset: str | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
    output: str = "json",
) -> dict[str, Any]:
    """Find drillhole collar records by bbox or exact collar selectors."""
    payload = _parse_model(
        DrillholeLocationsInput,
        {
            "bbox": bbox,
            "collar_id": collar_id,
            "hole_id": hole_id,
            "company_hole_id": company_hole_id,
            "dataset": dataset,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
            "output": output,
        },
    )
    params = _selector_params(payload)
    params.update({"limit": payload.limit, "offset": payload.offset, "output": payload.output})
    return await _query_table("dbo_collar", params)


@mcp.tool()
async def gswa_get_drillhole_family(
    collar_id: int | None = None,
    hole_id: str | None = None,
    company_hole_id: str | None = None,
    dataset: str | None = None,
    anumber: int | None = None,
    include_mrt: bool = False,
    limit_per_table: int = 1000,
) -> dict[str, Any]:
    """Return all raw GSWA rows related to matching drillhole collars."""
    config = load_config()
    payload = _parse_model(
        DrillholeFamilyInput,
        {
            "collar_id": collar_id,
            "hole_id": hole_id,
            "company_hole_id": company_hole_id,
            "dataset": dataset,
            "anumber": anumber,
            "include_mrt": include_mrt,
            "limit_per_table": limit_per_table,
        },
    )
    params = _selector_params(payload)
    params.update(
        {
            "include_mrt": payload.include_mrt,
            "limit_per_table": clamp_limit(payload.limit_per_table, config.max_records),
        }
    )
    async with DarkmineClient(config) as client:
        return await client.get(f"{RAW_GSWA_PREFIX}/collar-family", params=clean_dict(params))


@mcp.tool()
async def gswa_query_drillhole_geochemistry_raw(
    bbox: list[float] | None = None,
    collar_id: int | None = None,
    hole_id: str | None = None,
    company_hole_id: str | None = None,
    dataset: str | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Return raw drillhole geochemistry intervals and EAV key/value assay attributes.

    Raw EAV data is not equivalent to the flattened assay tables. Use this for
    source fidelity and traceability.
    """
    payload = _parse_model(
        DrillholeGeochemistryInput,
        {
            "bbox": bbox,
            "collar_id": collar_id,
            "hole_id": hole_id,
            "company_hole_id": company_hole_id,
            "dataset": dataset,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
        },
    )
    params = _selector_params(payload)
    params.update({"limit": payload.limit, "offset": payload.offset})
    attr_params = dict(params)

    parent = await _query_table("dbo_dhgeochemistry", params)
    attributes = await _query_table("dbo_dhgeochemistryattr", attr_params)
    return {
        "data": {
            "mode": "raw_eav",
            "parent_table": "dbo_dhgeochemistry",
            "attribute_table": "dbo_dhgeochemistryattr",
            "parents": parent["data"],
            "attributes": attributes["data"],
        },
        "usage": {
            "parents": parent.get("usage", {}),
            "attributes": attributes.get("usage", {}),
        },
    }


@mcp.tool()
async def gswa_query_drillhole_geochemistry_flat(
    bbox: list[float] | None = None,
    collar_id: int | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Return flattened drillhole assay rows from gsd_dhassayflat.

    Flat rows are convenient for analysis but are not equivalent to raw EAV data.
    """
    payload = _parse_model(
        DrillholeGeochemistryInput,
        {
            "bbox": bbox,
            "collar_id": collar_id,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
        },
    )
    params = _selector_params(payload)
    params.update(
        {
            "limit": payload.limit,
            "offset": payload.offset,
        }
    )
    return await _query_table("gsd_dhassayflat", params)


@mcp.tool()
async def gswa_query_drillhole_geochemistry_summary(
    bbox: list[float] | None = None,
    collar_id: int | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Return flattened per-hole assay summaries from gsd_dhassayflatsummary."""
    payload = _parse_model(
        DrillholeGeochemistryInput,
        {
            "bbox": bbox,
            "collar_id": collar_id,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
        },
    )
    params = _selector_params(payload)
    params.update(
        {
            "limit": payload.limit,
            "offset": payload.offset,
        }
    )
    return await _query_table("gsd_dhassayflatsummary", params)


@mcp.tool()
async def gswa_find_surface_samples(
    bbox: list[float] | None = None,
    surface_sample_id: int | None = None,
    sample_identifier: str | None = None,
    company_sample_id: str | None = None,
    sample_dataset: str | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Find raw surface sample location records by bbox or exact sample selectors."""
    payload = _parse_model(
        SurfaceSampleSelector,
        {
            "bbox": bbox,
            "surface_sample_id": surface_sample_id,
            "sample_identifier": sample_identifier,
            "company_sample_id": company_sample_id,
            "sample_dataset": sample_dataset,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
        },
    )
    params = _selector_params(payload)
    params.update({"limit": payload.limit, "offset": payload.offset})
    return await _query_table("dbo_surfacesample", params)


@mcp.tool()
async def gswa_get_surface_sample_family(
    surface_sample_id: int | None = None,
    sample_identifier: str | None = None,
    company_sample_id: str | None = None,
    sample_dataset: str | None = None,
    anumber: int | None = None,
    include_mrt: bool = False,
    limit_per_table: int = 1000,
) -> dict[str, Any]:
    """Return all raw GSWA rows related to matching surface samples."""
    config = load_config()
    payload = _parse_model(
        SurfaceSampleFamilyInput,
        {
            "surface_sample_id": surface_sample_id,
            "sample_identifier": sample_identifier,
            "company_sample_id": company_sample_id,
            "sample_dataset": sample_dataset,
            "anumber": anumber,
            "include_mrt": include_mrt,
            "limit_per_table": limit_per_table,
        },
    )
    params = _selector_params(payload)
    params.update(
        {
            "include_mrt": payload.include_mrt,
            "limit_per_table": clamp_limit(payload.limit_per_table, config.max_records),
        }
    )
    async with DarkmineClient(config) as client:
        return await client.get(
            f"{RAW_GSWA_PREFIX}/surface-sample-family",
            params=clean_dict(params),
        )


@mcp.tool()
async def gswa_query_surface_geochemistry_raw(
    bbox: list[float] | None = None,
    surface_sample_id: int | None = None,
    sample_identifier: str | None = None,
    company_sample_id: str | None = None,
    sample_dataset: str | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Return raw surface sample rows and EAV key/value geochemistry attributes.

    Raw EAV data is not equivalent to the flattened assay table. Use this for
    source fidelity and traceability.
    """
    payload = _parse_model(
        SurfaceGeochemistryInput,
        {
            "bbox": bbox,
            "surface_sample_id": surface_sample_id,
            "sample_identifier": sample_identifier,
            "company_sample_id": company_sample_id,
            "sample_dataset": sample_dataset,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
        },
    )
    params = _selector_params(payload)
    params.update({"limit": payload.limit, "offset": payload.offset})
    attr_params = dict(params)

    samples = await _query_table("dbo_surfacesample", params)
    attributes = await _query_table("dbo_surfacesampleattr", attr_params)
    return {
        "data": {
            "mode": "raw_eav",
            "parent_table": "dbo_surfacesample",
            "attribute_table": "dbo_surfacesampleattr",
            "samples": samples["data"],
            "attributes": attributes["data"],
        },
        "usage": {
            "samples": samples.get("usage", {}),
            "attributes": attributes.get("usage", {}),
        },
    }


@mcp.tool()
async def gswa_query_surface_geochemistry_flat(
    bbox: list[float] | None = None,
    surface_sample_id: int | None = None,
    anumber: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Return flattened surface sample assay rows from gsd_ssassayflat.

    Flat rows are convenient for analysis but are not equivalent to raw EAV data.
    """
    payload = _parse_model(
        SurfaceGeochemistryInput,
        {
            "bbox": bbox,
            "surface_sample_id": surface_sample_id,
            "anumber": anumber,
            "limit": limit,
            "offset": offset,
        },
    )
    params = _selector_params(payload)
    params.update(
        {
            "limit": payload.limit,
            "offset": payload.offset,
        }
    )
    return await _query_table("gsd_ssassayflat", params)


def build_server(config: DarkmineConfig | None = None) -> FastMCP:
    """Build the MCP server and optionally fail fast on supplied config."""
    if config is None:
        load_config()
    return mcp


def main() -> None:
    try:
        build_server()
        mcp.run()
    except DarkmineError as exc:
        raise SystemExit(str(exc)) from exc
