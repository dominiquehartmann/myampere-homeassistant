# SPDX-FileCopyrightText: Copyright the myAmpere contributors
# SPDX-License-Identifier: MIT
"""Keeps the data of one myAmpere server: live values by push, the rest every minute."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, CertificateMismatch, InvalidAuth, OpenAmpereClient, OpenAmpereError
from .app import async_check_app
from .const import CONF_MIN_INTERVAL, DEFAULT_MIN_INTERVAL_S, DOMAIN, STATE_INTERVAL_S

APP_CHECK_S = 300  # while myAmpere does not answer: is the Home Assistant app still installed? (#300)
# failed queries in a row that keep the entities while live values still come: one slow answer (e.g. behind a
# Modbus proxy) must not make every entity unavailable for a minute (#336)
MAX_MISSED_STATES = 3

_LOGGER = logging.getLogger(__name__)


PRICES_S = 900  # the import prices change every quarter hour
FORECAST_S = 3600  # the solar forecast is updated a few times a day
PLAN_S = 300  # the charging plan follows the prices and the state of charge
HEALTH_S = 3600  # the state of health changes over months
EVCC_S = 60  # evcc and the heat pump change with the car and the weather


class OpenAmpereCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: OpenAmpereClient, info: dict) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN,
                         update_interval=timedelta(seconds=STATE_INTERVAL_S))
        self.client = client
        self.info = info
        self._read_at: dict[str, float] = {}  # when prices and forecast were asked for last
        self.live_connected = False
        self._last_push = 0.0
        self._listener: asyncio.Task | None = None
        self._reload_scheduled = False
        self._app_checked = 0.0
        self._missed_states = 0

    @property
    def can_control(self) -> bool:
        return self.info["token"]["scope"] == "control"

    def async_update_listeners(self) -> None:
        self._follow_firmware()
        super().async_update_listeners()
        data = self.data or {}
        if not self._reload_scheduled and self.config_entry and needs_reload(self.info, data.get("live"),
                                                                           data.get("wallboxes"), data.get("status")):
            self._reload_scheduled = True
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    def _follow_firmware(self) -> None:
        """The device info has the firmware from the setup: keep it current after an update of the inverter."""
        device = self.info.get("device")
        current = firmware(self)
        if not device or current is None or current == device.get("firmware"):
            return
        device["firmware"] = current
        if not self.config_entry:
            return
        registry = dr.async_get(self.hass)
        # not async_get_device (deprecated) nor its successor (newer than the oldest Home Assistant supported)
        identifier = (DOMAIN, self.info["installation_id"])
        for entry in dr.async_entries_for_config_entry(registry, self.config_entry.entry_id):
            if identifier in entry.identifiers:
                registry.async_update_device(entry.id, hw_version=current)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.client.state()
        except (InvalidAuth, CertificateMismatch) as err:
            # revoked token or a different server/certificate: ask for a new connection code
            raise ConfigEntryAuthFailed(str(err)) from err
        except (CannotConnect, OpenAmpereError) as err:
            if self.live_connected and self.data is not None and self._missed_states < MAX_MISSED_STATES:
                self._missed_states += 1
                _LOGGER.debug("myAmpere state not fetched (%d/%d): %s", self._missed_states, MAX_MISSED_STATES, err)
                return self.data
            if self.config_entry and time.monotonic() - self._app_checked > APP_CHECK_S:
                self._app_checked = time.monotonic()
                self.config_entry.async_create_background_task(
                    self.hass, async_check_app(self.hass, self.config_entry), f"{DOMAIN} app check")
            raise UpdateFailed(str(err)) from err
        self._missed_states = 0
        return {**(self.data or {}), **state, **await self._slow_reads()}

    async def _slow_reads(self) -> dict[str, Any]:
        """Prices and forecast change slowly: fetched on their own intervals; an older answer stays if a request fails."""
        return {"prices": await self._cached("prices", self.client.prices, PRICES_S),
                "forecast": await self._cached("forecast", self.client.forecast, FORECAST_S),
                "charging_plan": await self._cached("charging_plan", self.client.charging_plan, PLAN_S),
                "battery_health": await self._cached("battery_health", self.client.battery_health, HEALTH_S),
                "evcc": await self._cached("evcc", self.client.evcc_loadpoints, EVCC_S),
                "heating": await self._cached("heating", self.client.heating, EVCC_S),
                "gridmeter": await self._cached("gridmeter", self.client.gridmeter, HEALTH_S),
                "cars": await self._cached("cars", self.client.cars, EVCC_S),
                "outages": await self._cached("outages", self.client.outages, EVCC_S),
                "charging_sessions": await self._cached("charging_sessions", self.client.charging_sessions, EVCC_S),
                "gridmeter_days": await self._cached("gridmeter_days", self.client.gridmeter_days, HEALTH_S),
                "surplus_order": await self._cached("surplus_order", self.client.surplus_order, EVCC_S)}

    async def _cached(self, name: str, fetch, every: float) -> dict | None:
        if time.monotonic() - self._read_at.get(name, float("-inf")) < every:
            return (self.data or {}).get(name)
        self._read_at[name] = time.monotonic()
        try:
            return await fetch()
        except (CannotConnect, OpenAmpereError) as err:
            _LOGGER.debug("myAmpere %s not fetched: %s", name, err)
            return (self.data or {}).get(name)

    def start_listening(self) -> None:
        self._listener = self.config_entry.async_create_background_task(
            self.hass, self.client.listen(self._on_push, self._on_live_connection), f"{DOMAIN} live values")

    def _on_push(self, message: dict) -> None:
        if message.get("type") != "live" or self.data is None:
            return
        min_interval = self.config_entry.options.get(CONF_MIN_INTERVAL, DEFAULT_MIN_INTERVAL_S)
        now = time.monotonic()
        if min_interval and now - self._last_push < min_interval:
            return  # fewer values for small systems (e.g. a Raspberry Pi with an SD card)
        self._last_push = now
        # not async_set_updated_data: that would restart the minute timer on every push and the settings would
        # never be fetched again
        self.data = {**self.data, **{k: message[k] for k in ("live", "status", "devices", "wallboxes")
                                         if k in message}}
        self.async_update_listeners()

    def _on_live_connection(self, connected: bool) -> None:
        if connected != self.live_connected:
            self.live_connected = connected
            if self.data is not None:
                self.async_update_listeners()


def firmware(coordinator: OpenAmpereCoordinator) -> str | None:
    """Firmware of the inverter: from the state, which follows an update; an older myAmpere has it only in /info."""
    status = (coordinator.data or {}).get("status") or {}
    if "firmware" in status:
        return status["firmware"]
    return (coordinator.info.get("device") or {}).get("firmware")


def needs_reload(info: dict, live: dict | None, wallboxes: list | None = None, status: dict | None = None) -> bool:
    """Set up before myAmpere had its first reading (e.g. everything starting after a power cut): the device and
    the PV inputs were unknown, so set up again once they are there (#220). Also when a wallbox was added or removed
    in myAmpere (#388), or a second PV inverter switched on, off or renamed (#419); an older myAmpere sends
    neither. And when the device got an access token or lost it (#538): the sensor of its days left comes or goes."""
    if status and "pv_external" in status and "pv_external" in info and status["pv_external"] != info["pv_external"]:
        return True
    if status and "token_days_left" in status and "token_sensor" in info \
            and (status["token_days_left"] is not None) != info["token_sensor"]:
        return True
    if wallboxes is not None and "wallboxes" in info \
            and sorted(w["id"] for w in wallboxes) != sorted(w["id"] for w in info["wallboxes"]):
        return True
    if not live:
        return False
    if info["device"] is None:
        return True
    count = info.get("pv_input_count")  # all inputs, also hidden ones; missing on older myAmpere versions
    return count is not None and len(live.get("pv_inputs") or []) != count
