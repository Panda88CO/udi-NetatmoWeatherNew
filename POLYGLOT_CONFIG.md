## Netatmo Weather NodeServer Configuration

#### Configuration Parameters:

- **shortPoll**: Time (in seconds) between heartbeats and local driver updates (e.g. `Time since measurement`). Real-time sensor updates are pushed via Netatmo webhooks.
- **longPoll**: Time (in seconds) between refreshes of cloud summary data (daily min/max temperatures, max wind, trends) and OAuth token checks.

#### Custom Configuration Parameters:

- **clientID**: Client ID from your Netatmo Developer App (`https://dev.netatmo.com`).
- **clientSecret**: Client Secret from your Netatmo Developer App (`https://dev.netatmo.com`).
- **TEMP_UNIT**: Temperature reporting unit (`C` or `F`).
- **WEBHOOK_URL**: Auto-populated ISY Portal webhook URL (`https://my.isy.io/api/eisy/pg3/webhook/noresponse/<uuid>/<slot>`). Ensure PG3 Remote Connection is enabled at `https://my.isy.io` (`Select Tool | PG3 | Remote connection` -> `Current status: Connected`). You can also paste this URL into the **Webhook URI** field of your Netatmo Developer App.
- **`<HomeName>_<StationName>`**: Select (`1`) or disable (`0`) each discovered Netatmo weather station.

