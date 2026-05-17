# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

import pytest

from darkmine_data_mcp import server
from darkmine_data_mcp.errors import DarkmineValidationError
from darkmine_data_mcp.models import (
    DrillholeLocationsInput,
    QueryRowsInput,
    SurfaceSampleSelector,
    clamp_limit,
)


def test_bbox_validation():
    with pytest.raises(ValueError, match="bbox longitudes"):
        DrillholeLocationsInput.model_validate({"bbox": [-181, -31, 120, -30]})


def test_limit_validation():
    with pytest.raises(DarkmineValidationError, match="no greater than 100"):
        clamp_limit(101, 100)


def test_generic_query_requires_filter_for_non_lookup_table():
    with pytest.raises(ValueError, match="At least one filter"):
        QueryRowsInput.model_validate({"table_name": "dbo_collar"})


def test_generic_query_allows_unfiltered_lookup_table():
    payload = QueryRowsInput.model_validate({"table_name": "cfg_lookupholetype"})

    assert payload.table_name == "cfg_lookupholetype"


def test_scoped_tools_require_selectors():
    with pytest.raises(ValueError, match="At least one drillhole selector"):
        DrillholeLocationsInput.model_validate({"limit": 10})

    with pytest.raises(ValueError, match="At least one surface-sample selector"):
        SurfaceSampleSelector.model_validate({"limit": 10})


@pytest.mark.asyncio
async def test_gswa_query_table_maps_bbox_to_rows_params(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, path, params=None):
            calls.append((path, params))
            return {"data": {"rows": []}, "usage": {"mb_used": 0.1}}

    monkeypatch.setenv("DARKMINE_DATA_API_KEY", "dm_test")
    monkeypatch.setattr(server, "DarkmineClient", FakeClient)

    result = await server.gswa_query_table(
        table_name="gsd_ssassayflat",
        bbox=[115.0, -32.0, 116.0, -31.0],
        limit=25,
    )

    assert result["usage"]["mb_used"] == 0.1
    assert calls == [
        (
            "/v1/raw/gswa/tables/gsd_ssassayflat/rows",
            {
                "min_lon": 115.0,
                "min_lat": -32.0,
                "max_lon": 116.0,
                "max_lat": -31.0,
                "limit": 25,
                "offset": 0,
                "output": "json",
            },
        )
    ]


@pytest.mark.asyncio
async def test_gswa_drillhole_raw_queries_parent_and_attr_tables(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, path, params=None):
            calls.append((path, params))
            return {"data": {"table_path": path}, "usage": {"mb_used": 0.1}}

    monkeypatch.setenv("DARKMINE_DATA_API_KEY", "dm_test")
    monkeypatch.setattr(server, "DarkmineClient", FakeClient)

    result = await server.gswa_query_drillhole_geochemistry_raw(hole_id="ABC123", limit=50)

    assert result["data"]["mode"] == "raw_eav"
    assert result["data"]["parent_table"] == "dbo_dhgeochemistry"
    assert result["data"]["attribute_table"] == "dbo_dhgeochemistryattr"
    assert calls == [
        (
            "/v1/raw/gswa/tables/dbo_dhgeochemistry/rows",
            {"hole_id": "ABC123", "limit": 50, "offset": 0},
        ),
        (
            "/v1/raw/gswa/tables/dbo_dhgeochemistryattr/rows",
            {"hole_id": "ABC123", "limit": 50, "offset": 0},
        ),
    ]


@pytest.mark.asyncio
async def test_gswa_surface_flat_uses_flat_surface_table(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, path, params=None):
            calls.append((path, params))
            return {"data": {"rows": []}, "usage": {}}

    monkeypatch.setenv("DARKMINE_DATA_API_KEY", "dm_test")
    monkeypatch.setattr(server, "DarkmineClient", FakeClient)

    await server.gswa_query_surface_geochemistry_flat(
        bbox=[115.0, -32.0, 116.0, -31.0],
        limit=100,
    )

    assert calls == [
        (
            "/v1/raw/gswa/tables/gsd_ssassayflat/rows",
            {
                "min_lon": 115.0,
                "min_lat": -32.0,
                "max_lon": 116.0,
                "max_lat": -31.0,
                "limit": 100,
                "offset": 0,
            },
        )
    ]


@pytest.mark.asyncio
async def test_gswa_family_uses_family_route_without_bbox(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, path, params=None):
            calls.append((path, params))
            return {"data": {}, "usage": {}}

    monkeypatch.setenv("DARKMINE_DATA_API_KEY", "dm_test")
    monkeypatch.setattr(server, "DarkmineClient", FakeClient)

    await server.gswa_get_drillhole_family(hole_id="ABC123", include_mrt=True, limit_per_table=20)

    assert calls == [
        (
            "/v1/raw/gswa/collar-family",
            {"hole_id": "ABC123", "include_mrt": True, "limit_per_table": 20},
        )
    ]
