
# Netatmo Weather Station NodeServer

Netatmo Weather Station NodeServer for PG3x
MIT license.

This node server integrates the Netatmo Weather Station using the latest Netatmo API (`/homesdata`, `/homestatus`, and [Netatmo Webhooks](https://dev.netatmo.com/apidocumentation/webhooks)) so real-time station and module updates are pushed via webhooks rather than relying on constant short-interval polling.

### Authentication
Authentication uses standard OAuth2. 
- **Shared Credentials (Recommended)**: If Client ID and Client Secret are pre-configured in PG3's OAuth Configuration (like `udi-nuheatv2`), simply click **Authenticate** in the PG3 dashboard.
- **Custom Developer App (Optional)**: If you prefer using your own developer credentials, log in at the [Netatmo Developer Portal](https://dev.netatmo.com), navigate to **My Apps** -> **Create**, and enter your `clientID` and `clientSecret` in the node server's Configuration parameters.

> [!NOTE]
> When updating or changing the Client ID and Client Secret, always click **Authenticate** in PG3. The node server automatically deletes any previous webhook subscriptions on Netatmo and re-establishes a fresh webhook bound to the new credentials, ensuring HMAC signature verification (`X-Netatmo-secret`) and event delivery remain valid.

## Enabling External Webhook Access (PG3x Remote Connection)

Because Netatmo sends real-time sensor events to your eISY/Polisy via the Universal Devices ISY Portal webhook endpoint:
1. Log in to [https://my.isy.io](https://my.isy.io).
2. Navigate to **Select Tool | PG3 | Remote connection**.
3. Ensure the remote connection is enabled and reads **"Current status: Connected"** (it may take up to a minute after switching it on to take effect).
4. During startup (or when pressing **Test Connection** on the controller node in the Admin Console), the node server performs an end-to-end webhook test through `https://my.isy.io/api/eisy/pg3/webhook/noresponse/<uuid>/<slot>`, verifies/registers the webhook endpoint automatically with Netatmo (via `POST /webhooks/v1/`), and reports the status in the **Webhook Test** (`GV30`) and **Connection Status** (`GV29`) drivers.

## Installation

1. Backup your ISY/eISY/Polisy in case of problems!
2. Enable PG3 Remote Connection at [https://my.isy.io](https://my.isy.io) (`Select Tool | PG3 | Remote connection` -> `Current status: Connected`).
3. Go to the Polyglot Store in the UI and install.
4. Add the NodeServer in PG3x (note: PG3 is not supported as the OAuth/Webhook library requires PG3x).
5. If credentials are not pre-configured in PG3 OAuth Configuration, enter your optional `clientID` and `clientSecret` under **Configuration** (see below) and restart.
6. Authenticate when prompted: press the **Authenticate** button, log in with your Netatmo account credentials, press **Accept**, and you will be returned to the PG3x interface.
7. Select which weather stations to use in Configuration (newly discovered stations default to `0`; set to `1` to enable) and restart the node server.
8. Open the Admin Console to view your controller and weather station module nodes.

### Node Settings & Drivers
The settings and drivers for this node are:

#### Short Poll
   * Sends a heartbeat (`DON`/`DOF`) and updates local drivers (such as `Time since measurement`). Real-time measurements are received via Netatmo webhooks (with automatic fallback to `/homestatus` if webhooks are not active). Default is 5 minutes.
#### Long Poll
   * Refreshes OAuth tokens and queries Netatmo cloud summary data (such as daily min/max temperatures, max wind, and trends). Default is 30 minutes.

#### Connection Status (`GV29`)
   * Reports `1` when real-time Netatmo webhook delivery is connected and active; reports `0` when operating in polling fallback mode.

#### Webhook Test (`GV30`)
   * Result of the portal loopback self-test (`0: None`, `1: Testing`, `2: Success`, `3: Timeout`, `4: Failure`).

#### Last Update (`uom 151`)
   * Unix timestamp of the most recent weather telemetry received (present on Controller `GV28` and all sensor nodes).

#### clientID (Optional)
   * Your Netatmo App Client ID (optional if configured in PG3 OAuth Configuration)

#### clientSecret (Optional)
   * Your Netatmo App Client Secret (optional if configured in PG3 OAuth Configuration)

#### TEMP_UNIT
   * `C` (default) or `F`

#### Weather Stations (`<HomeName>_<StationName>`)
   * Weather stations associated with the account are listed (default `0`) — set to `1` to include or `0` to disable, then restart.

## Requirements

   * PG3x ver 3.2.27 or greater
   * `udi_interface` 3.3.10 or greater
   * Active Universal Devices Portal (`my.isy.io`) license with PG3 Remote Connection enabled

# Release Notes
Code originally based on the NetatmoWeather node server and updated for OAuth2 and Netatmo Webhooks.

- 1.2.0 11/06/2026
   - Migrated to dynamic node definitions (`MAINUNITC`/`MAINUNITF`, `INDOORC`/`INDOORF`, `OUTDOORC`/`OUTDOORF`) loaded according to configured temperature unit (`TEMP_UNIT`)
   - Eliminated multi-unit ranges and `uom="25"` fallbacks in numeric and measurement editors to fix eISY program evaluation issues
   - Normalized all editor IDs and node definition IDs to uppercase with no underscores (`CONTROLLER`, `MAINUNITC`, `MAINUNITF`, `INDOORC`, `INDOORF`, `OUTDOORC`, `OUTDOORF`, `WIND`, `RAIN`)
   - Initialized driver lists and offline states with proper measurement UOMs instead of defaulting to index UOM 25
- 1.1.1 11/05/2026
   - Supported PG3 OAuth Configuration for shared client credentials (like `udi-nuheatv2`)
   - Enhanced webhook event debugging and modern `/webhooks/v1/` registration lifecycle
   - Added automatic webhook drop and re-establishment when re-authenticating with new credentials
   - Added `Last Update` timestamp driver (`uom 151`) across controller and all sensor modules
- 1.1.0 11/05/2026
   - Updated to use the latest Netatmo API with real-time Webhooks (`https://dev.netatmo.com/apidocumentation/webhooks`) instead of short-poll API polling
   - Added startup webhook self-test (`Webhook Test` driver `GV30`, `Connection Status` driver `GV29`, and `Test Connection` command) like `TeslaEV3`
   - Added automatic `/addwebhook` / `/dropwebhook` lifecycle management
   - Fixed timestamp, wind/gust field mapping, and online status merging between `/homestatus`, webhooks, and cloud data
- 0.1.2
   - Maintenance and OAuth updates
- 0.1.0 02/07/2024
   - Initial version published to GitHub

