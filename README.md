# Netatmo Weather Station NodeServer

Netatmo Weather Station NodeServer for PG3, PG3x
MIT license.

This node server integrates the Netatmo Weather Station. You will need account access to your Netatmo via the Netatmo Developer API https://dev.netatmo.com. Log in, select **My Apps**, and then **Create**. Fill in the application information and save — this exposes a **Client ID** and **Client Secret**.

Start the node server under PG3x — go to **Configuration** and enter your Client ID and Client Secret, then restart. The first time you do this, you should see a notice asking to authenticate. Click the **Authenticate** button — you will be taken to Netatmo's login page where you enter your Netatmo credentials. Press **Accept** to authorize and you will be returned to the PG3 interface.

After running, the detected weather stations under the account will be listed in Configuration. By default, all stations are active (`1`). If you do not want a station included, set its value to `0` and restart.

## Installation

1. Backup your ISY/IoX in case of problems!
2. Install the node server from the Polyglot Store in the PG3x UI.
3. Open the node server Configuration and enter your `ClientID` and `ClientSecret`.
4. Restart the node server.
5. Authenticate via the OAuth prompt when requested.
6. Select weather stations to be included in configuration (`1` to enable, `0` to disable).
7. Restart the node server.
8. Open the Admin Console.

### Node Settings

#### Short Poll
* Query Weather Station instantaneous data. The default is 5 minutes (sends a heartbeat pulse `DON` / `DOF`).

#### Long Poll
* Query Weather Station full cloud data. Netatmo weather data updates every ~10–15 minutes. The default is 30 minutes.

#### ClientID
* Your Netatmo App Client ID.

#### ClientSecret
* Your Netatmo App Client Secret.

#### TEMP_UNIT
* Temperature unit: `C` (default) or `F`.

#### Weather Stations
* Weather stations associated with the account are listed by station name — set to `1` to include or `0` to disable.

## Requirements

* PG3x ver 3.2.18 or greater
* udi_interface 3.1.1 or greater

# Release Notes

*Code based on the original NetatmoWeather node server (updated for modern OAuth authentication and PG3x).*

- **1.0.2** (10/24/2026)
  - Updated primary status (`ST`) on submodule nodes: Temperature for Indoor/Outdoor, Wind for Wind gauge, and Rain for Rain gauge.
  - Moved connection state to `GV9` (Connected) on all submodule nodes; Main node retains `ST` as Connected.
  - Reordered drivers and node definitions so `ST` is first and `TIME` is last.
  - Replaced "Time since measurement" with Epoch timestamp `TIME` (UOM 151) across all nodes.
  - `TIME` preserves the last valid timestamp and is not cleared on temporary communication loss or offline status.
  - Enabled Pressure Trend (`GV9`) on Main Station.
  - Fixed Outdoor module humidity (`CLIHUM`) reporting in online and offline states.
  - Fixed timestamp merge key overwrite bug (`ts` / `time_utc`).
  - Added `QUERY` command to all nodes and `DON`/`DOF` heartbeat commands to Controller.

- **1.0.1** (10/24/2026)
  - Standardized all nodeDef, editor, and driver IDs to uppercase with no special characters.
  - Added descriptive names to all drivers across all nodes.
  - Fixed startup crash when offline or empty stations exist in the account.
  - Robust exception and response handling for Netatmo API calls.

- **0.1.0** (02/07/2024)
  - Initial version published to GitHub.
