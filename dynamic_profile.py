#!/usr/bin/env python3
"""
Dynamic JSON Profile Definition for Netatmo Weather NodeServer
Follows the UDI dynamic JSON profile pattern (e.g. udi-kidde, udi-broadlink).
No static XML profile files needed.
"""


def build_profile_definition(temp_unit: str = "C") -> dict:
    """Build dynamic JSON profile dictionary for updateJsonProfile().

    TEMPERATURE editor range dynamically adjusts according to temp_unit ('C' or 'F').
    Single-unit range only, no multi-unit ambiguity, no uom 25 fallback.
    """
    is_fahrenheit = str(temp_unit or "C").strip().upper().startswith("F")
    temp_range = (
        {"uom": "17", "min": -50, "max": 150, "prec": 1}
        if is_fahrenheit
        else {"uom": "4", "min": -50, "max": 65, "prec": 1}
    )

    editors = [
        {
            "id": "BOOL",
            "ranges": [{"uom": "2", "subset": "0,1"}],
        },
        {
            "id": "STATUS",
            "ranges": [{"uom": "2", "subset": "0,1"}],
        },
        {
            "id": "TEMPERATURE",
            "ranges": [temp_range],
        },
        {
            "id": "CO2",
            "ranges": [{"uom": "54", "min": 0, "max": 10000, "prec": 0}],
        },
        {
            "id": "HUMIDITY",
            "ranges": [{"uom": "51", "min": 0, "max": 100, "prec": 0}],
        },
        {
            "id": "NOISE",
            "ranges": [{"uom": "12", "min": 0, "max": 1000, "prec": 0}],
        },
        {
            "id": "PRESSURE",
            "ranges": [{"uom": "117", "min": 0, "max": 10000, "prec": 0}],
        },
        {
            "id": "TREND",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,99",
                    "names": {
                        "0": "Stable",
                        "1": "Up",
                        "2": "Down",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "TIMESTAMP",
            "ranges": [{"uom": "44", "min": 0, "max": 525600, "prec": 0}],
        },
        {
            "id": "UNIXTIME",
            "ranges": [{"uom": "151", "min": 0, "max": 2147483647, "prec": 0}],
        },
        {
            "id": "PERCENT",
            "ranges": [{"uom": "51", "min": 0, "max": 100, "prec": 0}],
        },
        {
            "id": "RAIN",
            "ranges": [{"uom": "82", "min": 0, "max": 100000, "prec": 1}],
        },
        {
            "id": "WINDSTRENGTH",
            "ranges": [{"uom": "48", "min": 0, "max": 1000, "prec": 0}],
        },
        {
            "id": "WINDANGLE",
            "ranges": [{"uom": "76", "min": 0, "max": 360, "prec": 0}],
        },
        {
            "id": "BATTERY",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,3,4,5,99",
                    "names": {
                        "0": "Maximum",
                        "1": "Full",
                        "2": "High",
                        "3": "Medium",
                        "4": "Low",
                        "5": "Very Low",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "RFSTATUS",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,99",
                    "names": {
                        "0": "Strong",
                        "1": "Medium",
                        "2": "Low",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "RFSTRENGTH",
            "ranges": [{"uom": "131", "min": -174, "max": 30, "prec": 0}],
        },
        {
            "id": "STREAMSYNC",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,98,99",
                    "names": {
                        "0": "Disconnected",
                        "1": "Connected",
                        "98": "Error",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "TESTCON",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,3,4,98,99",
                    "names": {
                        "0": "Idle",
                        "1": "Testing...",
                        "2": "Success",
                        "3": "Timeout",
                        "4": "Failure",
                        "98": "Error",
                        "99": "Unknown",
                    },
                }
            ],
        },
    ]

    nodedefs = [
        {
            "id": "CONTROLLER",
            "name": "Netatmo System",
            "icon": "Weather",
            "properties": [
                {"id": "ST", "name": "NodeServer Online", "editor": "BOOL"},
                {"id": "GV28", "name": "Last Update", "editor": "UNIXTIME"},
                {"id": "GV29", "name": "Connection Status", "editor": "STREAMSYNC"},
                {"id": "GV30", "name": "Webhook Test", "editor": "TESTCON"},
            ],
            "cmds": {
                "accepts": [
                    {"id": "UPDATE", "name": "Force Update"},
                    {"id": "TESTCON", "name": "Test Connection"},
                ],
                "sends": [
                    {"id": "DON", "name": "Heartbeat On"},
                    {"id": "DOF", "name": "Heartbeat Off"},
                ],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "MAINUNIT",
            "name": "Main Weather Station",
            "icon": "Weather",
            "properties": [
                {"id": "ST", "name": "Connected", "editor": "BOOL"},
                {"id": "CLITEMP", "name": "Temperature", "editor": "TEMPERATURE"},
                {"id": "CO2LVL", "name": "CO2", "editor": "CO2"},
                {"id": "CLIHUM", "name": "Humidity", "editor": "HUMIDITY"},
                {"id": "GV3", "name": "Noise", "editor": "NOISE"},
                {"id": "BARPRES", "name": "Pressure", "editor": "PRESSURE"},
                {"id": "GV5", "name": "Absolute Pressure", "editor": "PRESSURE"},
                {"id": "GV6", "name": "Min Temperature", "editor": "TEMPERATURE"},
                {"id": "GV7", "name": "Max Temperature", "editor": "TEMPERATURE"},
                {"id": "GV8", "name": "Temperature Trend", "editor": "TREND"},
                {"id": "GV10", "name": "Time since measurement", "editor": "TIMESTAMP"},
                {"id": "GV11", "name": "Wi-Fi Status", "editor": "RFSTATUS"},
                {"id": "GV12", "name": "Last Update", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [{"id": "UPDATE", "name": "Force Update"}],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "INDOOR",
            "name": "Indoor Module",
            "icon": "Weather",
            "properties": [
                {"id": "ST", "name": "Connected", "editor": "BOOL"},
                {"id": "CLITEMP", "name": "Temperature", "editor": "TEMPERATURE"},
                {"id": "CO2LVL", "name": "CO2", "editor": "CO2"},
                {"id": "CLIHUM", "name": "Humidity", "editor": "HUMIDITY"},
                {"id": "GV3", "name": "Min Temperature", "editor": "TEMPERATURE"},
                {"id": "GV4", "name": "Max Temperature", "editor": "TEMPERATURE"},
                {"id": "GV5", "name": "Temperature Trend", "editor": "TREND"},
                {"id": "GV6", "name": "Time since measurement", "editor": "TIMESTAMP"},
                {"id": "GV7", "name": "Battery", "editor": "BATTERY"},
                {"id": "GV8", "name": "RF Status", "editor": "RFSTATUS"},
                {"id": "GV9", "name": "Last Update", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [{"id": "UPDATE", "name": "Force Update"}],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "OUTDOOR",
            "name": "Outdoor Module",
            "icon": "Weather",
            "properties": [
                {"id": "ST", "name": "Connected", "editor": "BOOL"},
                {"id": "CLITEMP", "name": "Temperature", "editor": "TEMPERATURE"},
                {"id": "CLIHUM", "name": "Humidity", "editor": "HUMIDITY"},
                {"id": "GV2", "name": "Min Temperature", "editor": "TEMPERATURE"},
                {"id": "GV3", "name": "Max Temperature", "editor": "TEMPERATURE"},
                {"id": "GV4", "name": "Temperature Trend", "editor": "TREND"},
                {"id": "GV5", "name": "Time since measurement", "editor": "TIMESTAMP"},
                {"id": "GV6", "name": "Battery", "editor": "BATTERY"},
                {"id": "GV7", "name": "RF Status", "editor": "RFSTATUS"},
                {"id": "GV8", "name": "Last Update", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [{"id": "UPDATE", "name": "Force Update"}],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "WIND",
            "name": "Wind Module",
            "icon": "Weather",
            "properties": [
                {"id": "ST", "name": "Connected", "editor": "BOOL"},
                {"id": "GV0", "name": "Wind Strength", "editor": "WINDSTRENGTH"},
                {"id": "GV1", "name": "Wind Angle", "editor": "WINDANGLE"},
                {"id": "GV2", "name": "Gust Strength", "editor": "WINDSTRENGTH"},
                {"id": "GV3", "name": "Gust Angle", "editor": "WINDANGLE"},
                {"id": "GV4", "name": "Max Wind Strength", "editor": "WINDSTRENGTH"},
                {"id": "GV5", "name": "Max Wind Angle", "editor": "WINDANGLE"},
                {"id": "GV6", "name": "Time since measurement", "editor": "TIMESTAMP"},
                {"id": "GV7", "name": "Battery", "editor": "BATTERY"},
                {"id": "GV8", "name": "RF Status", "editor": "RFSTATUS"},
                {"id": "GV9", "name": "Last Update", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [{"id": "UPDATE", "name": "Force Update"}],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "RAIN",
            "name": "Rain Module",
            "icon": "Weather",
            "properties": [
                {"id": "ST", "name": "Connected", "editor": "BOOL"},
                {"id": "GV0", "name": "Rain", "editor": "RAIN"},
                {"id": "GV1", "name": "Sum Rain 1h", "editor": "RAIN"},
                {"id": "GV2", "name": "Sum Rain 24h", "editor": "RAIN"},
                {"id": "GV3", "name": "Time since measurement", "editor": "TIMESTAMP"},
                {"id": "GV4", "name": "Battery", "editor": "BATTERY"},
                {"id": "GV5", "name": "RF Status", "editor": "RFSTATUS"},
                {"id": "GV6", "name": "Last Update", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [{"id": "UPDATE", "name": "Force Update"}],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
    ]

    return {
        "delete": {
            "editors": ["*"],
            "nodedefs": ["*"],
            "linkdefs": ["*"],
        },
        "editors": editors,
        "nodedefs": nodedefs,
        "linkdefs": [],
    }

