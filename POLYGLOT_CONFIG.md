## Netatmo Weather NodeServer Configuration

#### Configuration Parameters:

- **shortPoll**: Time (in seconds) between heartbeats and local driver updates (e.g. `Time since measurement`). Real-time sensor updates are pushed via Netatmo webhooks. Default is 300 (5 minutes).
- **longPoll**: Time (in seconds) between refreshes of cloud summary data (daily min/max temperatures, max wind, trends) and OAuth token checks. Default is 1800 (30 minutes).

#### Custom Configuration Parameters:

- **clientID** *(optional)*: Client ID from your Netatmo Developer App (`https://dev.netatmo.com`). Not required when credentials are provided via PG3 OAuth Configuration.
- **clientSecret** *(optional)*: Client Secret from your Netatmo Developer App (`https://dev.netatmo.com`). Not required when credentials are provided via PG3 OAuth Configuration.
- **TEMP_UNIT**: Temperature reporting unit (`C` or `F`). Default is `C`.
- **`<HomeName>_<StationName>`**: Discovered Netatmo weather stations default to `0` (disabled) on first run. Set to `1` to enable the station and modules, then restart the NodeServer.

#### Node Drivers & Status:

- **Connection Status (`GV29`)**: Shows whether real-time webhook push delivery is connected (`1`) or using polling fallback (`0`).
- **Webhook Test (`GV30`)**: Status of the startup portal loopback test (`0: None`, `1: Testing`, `2: Success`, `3: Timeout`, `4: Failure`).
- **Last Update (`uom 151`)**: Displays the Unix epoch timestamp of the most recent weather telemetry received (present on Controller `GV28` and all weather sensor nodes).

