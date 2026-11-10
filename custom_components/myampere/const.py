# SPDX-FileCopyrightText: Copyright the myAmpere contributors
# SPDX-License-Identifier: MIT
"""Constants of the myAmpere integration."""

from __future__ import annotations

DOMAIN = "myampere"
API_VERSION = 1  # /api/external/v1 of the myAmpere server

CONF_FINGERPRINT = "fingerprint"
CONF_TOKEN = "token"
CONF_CODE = "code"
CONF_MIN_INTERVAL = "min_interval"

CODE_PREFIX = "openampere1:"
STATE_INTERVAL_S = 60  # settings, price and the rest that changes slowly; live values come by push
DEFAULT_MIN_INTERVAL_S = 0  # 0 = every live value myAmpere sends

WORK_MODES = ["self_use", "feed_in_first", "backup", "peak_shaving"]
DEVICE_MODES = ["auto", "off", "boost"]
# wallboxes myAmpere controls itself (#388)
WALLBOX_MODES = ["manual", "off", "pv", "minpv", "now"]
WALLBOX_CHARGING_MODES = ["pv", "minpv", "now"]  # each with its own highest current (#409)
WALLBOX_STATES = ["idle", "plugged_in", "charging", "waiting", "paused", "finished", "fault", "unknown"]
