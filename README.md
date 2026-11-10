# myAmpere for Home Assistant

A Home Assistant integration for [myAmpere](https://github.com/dominiquehartmann/myampere), the local app for solar
systems with a home battery. It shows the values of your system in Home Assistant, including the energy dashboard,
and can control the battery and the own devices if you allow it.

It is an independent client: it works only while a myAmpere server runs on your network. It talks to the server's
external API and never to the inverter. Every command goes through the same checks as in the myAmpere app (control
switch, test mode, limits), and the server logs it with the name of the token.

This integration is not affiliated with the original project OpenAmpere or with the company that sold the systems
(EKD). Use it at your own risk; it is not legal or electrical advice.

## Requirements

- A running myAmpere server (Docker or the Home Assistant app), reachable from Home Assistant.
- Home Assistant with HACS, or copy the folder `custom_components/myampere` by hand.

## Installation

1. In HACS, open the menu, choose "Custom repositories", add `https://github.com/dominiquehartmann/myampere-homeassistant`
   as an integration, and install myAmpere.
2. Restart Home Assistant.
3. Open Settings → Devices & services → Add integration → myAmpere.
4. In the myAmpere app, open Mehr → Verbindung und create a connection code for Home Assistant. Enter it in the
   integration. Pairing, token and certificate are then stored by Home Assistant.

If a new certificate of the server comes up, pair again: the integration never accepts a changed certificate by itself.

## Entities

The integration offers everything the official OpenAmpere integration offers: power, energy and temperature sensors,
the battery mode and limits, grid charging, the mode of the own devices and the wallboxes that myAmpere controls.

Additionally it offers the import price of the current quarter hour, the solar forecast for today and tomorrow and the
next planned grid-charging quarter hour with its reason. These are switched off by default: switch on the ones you
need under the entity settings of the device.

Entities are added step by step as the server offers more data; the list in the integration is the one that counts.

## Development

Tests run in their own environment with the pinned versions:

    cd tests
    uv venv ../.venv-ha --python 3.14
    uv pip install -p ../.venv-ha -r requirements.lock
    ../.venv-ha/bin/pytest

Issues and pull requests are welcome in this repository. Please describe what the server answered and which version of
myAmpere you use.

## License

MIT. See [LICENSE](LICENSE).
