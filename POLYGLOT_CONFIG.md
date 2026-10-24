## Netatmo NodeServer Configuration

#### Configuration Parameters:

- **shortPoll**: Time between refresh of instantaneous data in seconds (default: 300).
- **longPoll**: Time between refresh of all cloud data in seconds (default: 1800).

#### Custom Configuration Parameters:

- **ClientID**: Client ID from your Netatmo Developer App.
- **ClientSecret**: Client Secret from your Netatmo Developer App.
- **TEMP_UNIT**: Temperature reporting unit (`C` or `F`, default: `C`).
- **<StationName>**: Enable (`1`) or disable (`0`) specific weather stations associated with your account.
