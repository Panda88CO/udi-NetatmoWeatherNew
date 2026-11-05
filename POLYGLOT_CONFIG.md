## Netatmo Weather NodeServer Configuration

#### Configuration Parameters:

- **shortPoll**: Time (in seconds) between heartbeats and local driver updates (e.g. `Time since measurement`). Real-time sensor updates are pushed via Netatmo webhooks.
- **longPoll**: Time (in seconds) between refreshes of cloud summary data (daily min/max temperatures, max wind, trends) and OAuth token checks.

#### Custom Configuration Parameters:

- **clientID**: Client ID from your Netatmo Developer App (`https://dev.netatmo.com`).
- **clientSecret**: Client Secret from your Netatmo Developer App (`https://dev.netatmo.com`).
- **TEMP_UNIT**: Temperature reporting unit (`C` or `F`).
- **`<HomeName>_<StationName>`**: Select (`1`) or disable (`0`, default) each discovered Netatmo weather station, then restart the NodeServer.

