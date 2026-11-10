# SPDX-FileCopyrightText: Copyright the OpenAmpere contributors
# SPDX-License-Identifier: MIT
"""Tests of the Home Assistant integration. The OpenAmpere server is replaced by a fake client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myampere.const import CONF_FINGERPRINT, CONF_TOKEN, DOMAIN

FINGERPRINT = "ab" * 32
INSTALLATION = "1f0e7c3a-0000-4000-8000-000000000001"
WALLBOX = "0a1b2c3d"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def info(scope: str = "control") -> dict:
    return {
        "api_version": 1, "version": "0.7.0", "installation_id": INSTALLATION,
        "token": {"name": "Home Assistant", "scope": scope},
        "device": {"manufacturer": "FoxESS", "model": "H3-10.0-Smart", "firmware": "1.40", "rated_power_w": 10000,
                   "supports_control": True},
        "pv_inputs": [{"index": 0, "name": "Süddach"}, {"index": 1, "name": "Westdach"}],
        "devices": [{"id": "rod1", "name": "Heizstab", "kind": "heating_rod"}],
        "wallboxes": [{"id": WALLBOX, "name": "Carport", "model": "dé Mobile Wallbox 11 kW (Tuya)"}],
        "poll_interval": 10, "web_port": 8080,
    }


def prices(now: float | None = None) -> dict:
    """Import prices per quarter hour, the current one first (ct/kWh gross)."""
    import time

    start = (time.time() if now is None else now) // 900 * 900
    return {"quarters": [{"ts": start + 900 * i, "price_ct": 20.0 + i} for i in range(4)]}


def forecast() -> dict:
    """Expected solar energy: day totals in kWh and the quarter hours (no location, as the server answers)."""
    return {"today_kwh": 12.3, "tomorrow_kwh": 9.8, "error": None, "fetched": 0, "quarters": []}


def state(control_enabled: bool = True) -> dict:
    return {
        "type": "state",
        "live": {"timestamp": 1.0, "pv_power": 5200.0, "house_power": 800.0, "grid_power": -3400.0,
                 "battery_power": -1000.0, "battery_soc": 63.0, "battery_soh": 98.0, "battery_voltage": 410.2,
                 "battery_current": -2.4, "battery_temperature": 24.5, "off_grid": False, "alarms": [0, 0, 0],
                 "temperatures": {"inverter": 41.0},
                 "pv_inputs": [{"power": 3000.0, "voltage": 400.0, "current": 7.5}, {"power": 2200.0, "voltage": 380.0, "current": 5.8}],
                 "totals": {"pv": 1234567.0, "load": 2345678.0, "grid_import": 345678.0, "grid_export": 456789.0,
                            "battery_charge": 56789.0, "battery_discharge": 45678.0, "consumption": 1112345.0}},
        "status": {"connected": True, "stale": False, "last_update": 1.0, "off_grid": False, "grid_charging": False,
                   "control": {"enabled": control_enabled, "dry_run": False}, "firmware": "1.40"},
        "devices": [{"id": "rod1", "name": "Heizstab", "kind": "heating_rod", "enabled": True, "power_w": 1500.0,
                     "on": True, "temperature_c": 52.5, "target_c": 60.0, "status": None, "error": None, "mode": "auto"}],
        "wallboxes": [{"id": WALLBOX, "name": "Carport", "enabled": True, "mode": "pv", "max_current_a": 16,
                       "mode_current_a": {"pv": 10, "minpv": 16, "now": 16}, "online": True,
                       "state": "charging", "connected": True, "charging": True, "power_w": 4140.0, "current_a": 6}],
        "battery_settings": {"work_mode": "self_use", "min_soc": 0, "max_soc": 100, "min_soc_on_grid": 24},
        "grid_charging": {"enabled": False, "target_soc": 80, "active": False},
        "price_ct": 31.5,
    }


@pytest.fixture
def entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, unique_id=INSTALLATION, title="OpenAmpere",
                           data={"host": "192.168.178.20", "port": 8443, CONF_FINGERPRINT: FINGERPRINT,
                                 CONF_TOKEN: "oa_secret"})


@pytest.fixture
def client():
    """The fake OpenAmpere: every method of the client is a mock."""
    base = "custom_components.myampere.api.OpenAmpereClient"
    energy = patch(f"{base}.device_energy", AsyncMock(return_value={"devices": [{"key": "c:rod1", "name": "Warmwasser", "kind": "heating_rod"}], "totals_wh": [4250.0], "entries": []}))
    energy_mock = energy.start()
    with patch(f"{base}.info", AsyncMock(return_value=info())) as info_mock, \
            patch(f"{base}.state", AsyncMock(return_value=state())) as state_mock, \
            patch(f"{base}.listen", AsyncMock(return_value=None)) as listen_mock, \
            patch(f"{base}.set_battery", AsyncMock(return_value={})) as battery_mock, \
            patch(f"{base}.set_grid_charging", AsyncMock(return_value={})) as charging_mock, \
            patch(f"{base}.set_device_mode", AsyncMock(return_value={})) as device_mock, \
            patch(f"{base}.set_wallbox_mode", AsyncMock(return_value={})) as wallbox_mock, \
            patch(f"{base}.prices", AsyncMock(return_value=prices())) as prices_mock, \
            patch(f"{base}.forecast", AsyncMock(return_value=forecast())) as forecast_mock, \
            patch(f"{base}.charging_plan", AsyncMock(return_value={"quarters": [], "reason": "Ladeziel erreicht"})) as plan_mock, \
            patch(f"{base}.battery_health", AsyncMock(return_value={"soh_pct": 97.5, "cycles": 120.0, "efficiency_pct": 88.0, "cell_max_now_c": 27.0, "capacity_kwh": 10.0})) as health_mock, \
            patch(f"{base}.evcc_loadpoints", AsyncMock(return_value={"configured": True, "error": None, "loadpoints": [{"id": 1, "title": "Garage", "heating": False, "power_w": 4100.0, "soc": 55.0}]})) as evcc_mock, \
            patch(f"{base}.heating", AsyncMock(return_value={"enabled": True, "setback_hours_today": 1.5, "plan": None})) as heating_mock, \
            patch(f"{base}.gridmeter", AsyncMock(return_value={"configured": True, "active_kinds": ["import"], "until": "2026-11-08", "synced": None, "error": None, "busy": False})) as meter_mock, \
            patch(f"{base}.export_limit", AsyncMock(return_value={"limit_w": 5000, "rated_power_w": 10000, "external_change": False, "unreadable": []})) as export_mock, \
            patch(f"{base}.gridmeter_days", AsyncMock(return_value={"import": {"2026-11-08": 6.25, "2026-11-09": 7.5}, "export": {"2026-11-09": 3.0}})) as days_mock, \
            patch(f"{base}.surplus_order", AsyncMock(return_value={"items": [{"key": "battery", "name": "Speicher", "kind": "battery"}, {"key": "c:1", "name": "Warmwasser", "kind": "heating_rod"}], "order": ["battery", "c:1"], "battery_soc": 50})) as order_mock, \
            patch(f"{base}.outages", AsyncMock(return_value={"current": None, "count": 2, "total_s": 900, "outages": []})) as outages_mock, \
            patch(f"{base}.charging_sessions", AsyncMock(return_value={"sessions": [{"finished": "2026-11-09T18:00:00", "energy_kwh": 11.5, "duration_s": 5400, "vehicle": "Golf", "loadpoint": "Garage", "solar_pct": None, "cost_eur": None}]})) as sessions_mock, \
            patch(f"{base}.cars", AsyncMock(return_value={"cars": [{"id": "car1", "name": "Golf", "brand": "VW", "enabled": True, "wallbox": None, "status": "ok", "checked": None, "values": {"soc": 64.0, "range_km": 310.0, "target_soc": 80.0}, "error": None}]})) as cars_mock:
        yield type("Fake", (), {"info": info_mock, "state": state_mock, "listen": listen_mock,
                                "set_battery": battery_mock, "set_grid_charging": charging_mock,
                                "set_device_mode": device_mock, "set_wallbox_mode": wallbox_mock, "prices": prices_mock, "forecast": forecast_mock, "charging_plan": plan_mock, "battery_health": health_mock, "evcc_loadpoints": evcc_mock, "heating": heating_mock, "gridmeter": meter_mock, "cars": cars_mock, "outages": outages_mock, "gridmeter_days": days_mock, "export_limit": export_mock, "surplus_order": order_mock, "charging_sessions": sessions_mock, "device_energy": energy_mock})
        energy.stop()
