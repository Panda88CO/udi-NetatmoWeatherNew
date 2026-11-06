
#!/usr/bin/env python3
import time
from NetatmoOauth import NetatmoCloud 
import urllib.parse
from datetime import datetime, timezone

#from oauth import OAuth
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)



class NetatmoWeather (NetatmoCloud):
    def __init__(self, polyglot):
        super().__init__(polyglot, 'read_station')
        logging.info('NetatmoWeather initializing')
        self.poly = polyglot
        self._dev_list  = ['NAMain', 'NAModule1', 'NAModule2', 'NAModule3', 'NAModule4']

        self.instant_data = {}
        self.cloud_data = {}
        self.weather_data = {}
        self.MAIN_modules = ['NAMain']
        self.OUTDOOR_modules = ['NAModule1']
        self.WIND_modules = ['NAModule2']
        self.RAIN_modules = ['NAModule3']
        self.INDOOR_modules = ['NAModule4']
        #self.scope = "read_station"

    # should not be necesary - filtered by token    
    #def get_weather_stations (self):
    #    logging.debug('get_weather_stations')
    #    all_systems = 


    def update_weather_info_cloud(self, home_id):
        ''' Polls latest data stored in cloud - more data available'''
        logging.debug('get_weather_info_cloud')
        try:
            tmp = self.get_modules(home_id)
            logging.debug('tmp = {}'.format(tmp))
            if not tmp:
                return {}
            self.cloud_data[home_id] = {
                'MAIN': {},
                'INDOOR': {},
                'OUTDOOR': {},
                'RAIN': {},
                'WIND': {}
            }
            for dev_id in tmp:
                if tmp[dev_id]['type'] in self.MAIN_modules:
                    dev_id_str = urllib.parse.quote_plus(dev_id)
                    api_str = '/getstationsdata?device_id=' + str(dev_id_str) + '&get_favorites=false'
                    temp_data = self._callApi('GET', api_str)
                    logging.debug('dev Id {}, data: {} '.format(dev_id, temp_data))
                    if temp_data and 'status' in temp_data and temp_data['status'] == 'ok':
                        devices = temp_data.get('body', {}).get('devices', [])
                        if not devices:
                            continue
                        device_data = next(
                            (d for d in devices if (d.get('_id') or d.get('id')) == dev_id),
                            devices[0]
                        )
                        logging.debug('past temp data {}'.format(device_data))
                        main_entry = {}
                        if 'dashboard_data' in device_data:
                            main_entry.update(device_data['dashboard_data'])
                        main_entry['reachable'] = device_data.get('reachable', True)
                        main_entry['online'] = device_data.get('reachable', 'dashboard_data' in device_data)
                        if 'data_type' in device_data:
                            main_entry['data_type'] = device_data['data_type']
                        if 'wifi_status' in device_data and 'wifi_strength' not in main_entry:
                            main_entry['wifi_strength'] = device_data['wifi_status']
                        self.cloud_data[home_id]['MAIN'][dev_id] = main_entry
                        logging.debug('past main {}'.format(self.cloud_data))
                        for mod in device_data.get('modules', []):
                            mod_type = self.module_type(mod.get('type'))
                            if not mod_type:
                                continue
                            mod_id = mod.get('_id') or mod.get('id')
                            if not mod_id:
                                continue
                            logging.debug('{} {}c data {}, mod  {}'.format(mod_type, mod_id, self.cloud_data, mod))
                            mod_entry = {}
                            if 'dashboard_data' in mod:
                                mod_entry.update(mod['dashboard_data'])
                                mod_entry['online'] = mod.get('reachable', True)
                            else:
                                mod_entry['online'] = mod.get('reachable', False)
                            mod_entry['reachable'] = mod.get('reachable', mod_entry['online'])
                            if 'data_type' in mod:
                                mod_entry['data_type'] = mod['data_type']
                            if 'rf_status' in mod and 'rf_strength' not in mod_entry:
                                mod_entry['rf_strength'] = mod['rf_status']
                            if 'battery_vp' in mod and 'battery_level' not in mod_entry:
                                mod_entry['battery_level'] = mod['battery_vp']
                            self.cloud_data[home_id][mod_type][mod_id] = mod_entry
                        logging.debug('data before merge: {}'.format(self.cloud_data))
                        self.merge_data(home_id)
            return self.cloud_data
        except Exception as e:
            logging.error('update_weather_info_cloud failed : {}'.format(e))
            return {}

    def module_type(self, type):
        if type in self.MAIN_modules:
            return 'MAIN'
        elif type in self.OUTDOOR_modules:
            return 'OUTDOOR'
        elif type in self.INDOOR_modules:
            return 'INDOOR'
        elif type in self.RAIN_modules:
            return 'RAIN'
        elif type in self.WIND_modules:
            return 'WIND'
        return None

    def _ensure_instant_home(self, home_id):
        if home_id not in self.instant_data or not isinstance(self.instant_data[home_id], dict):
            self.instant_data[home_id] = {}
        for mtype in ('MAIN', 'OUTDOOR', 'INDOOR', 'RAIN', 'WIND'):
            if mtype not in self.instant_data[home_id]:
                self.instant_data[home_id][mtype] = {}

    def update_weather_info_instant(self, home_id):
        '''Polls latest data - within 10 sec '''
        logging.debug('update_weather_info_instant')
        tmp = self.get_home_status(home_id)
        self._ensure_instant_home(home_id)
        if tmp and 'modules' in tmp:
            for module in tmp['modules']:
                mod_info = tmp['modules'][module]
                mod_type = self.module_type(mod_info.get('type'))
                if mod_type:
                    self.instant_data[home_id][mod_type][module] = mod_info
        self.merge_data(home_id)
        return self.instant_data

    def _resolve_home_and_type(self, mod_id, home_id=None, raw_type=None):
        resolved_home = home_id
        resolved_type = raw_type
        if hasattr(self, 'homes_list') and self.homes_list:
            if resolved_home and resolved_home in self.homes_list:
                if mod_id in self.homes_list[resolved_home].get('modules', {}):
                    if not resolved_type:
                        resolved_type = self.homes_list[resolved_home]['modules'][mod_id].get('type')
            else:
                for h_id, h_data in self.homes_list.items():
                    if mod_id in h_data.get('modules', {}):
                        resolved_home = h_id
                        if not resolved_type:
                            resolved_type = h_data['modules'][mod_id].get('type')
                        break
        return resolved_home, resolved_type

    def process_webhook_data(self, payload):
        '''Processes incoming Netatmo webhook payload and updates instant_data + weather_data'''
        logging.info(f'[WEBHOOK EVENT] Processing payload: {payload}')
        updated_homes = set()
        if not isinstance(payload, dict):
            logging.warning(f'[WEBHOOK EVENT] Expected dict payload but received {type(payload)}: {payload}')
            return updated_homes

        push_type = payload.get('push_type') or payload.get('event_type')
        home_id = payload.get('home_id')
        device_id = payload.get('device_id') or payload.get('id')
        user_id = payload.get('user_id')
        event_ts = int(payload.get('time_stamp') or payload.get('ts') or payload.get('time_server') or int(time.time()))

        logging.info(
            f'[WEBHOOK EVENT] Event details: push_type="{push_type}", home_id="{home_id}", '
            f'device_id="{device_id}", user_id="{user_id}", timestamp={event_ts}'
        )

        if push_type == 'webhook_activation':
            logging.info('[WEBHOOK EVENT] Netatmo webhook activation handshake confirmed by Netatmo server!')
            return updated_homes
        if push_type == 'webhook_deletion':
            logging.warning(f'[WEBHOOK EVENT] Netatmo webhook deletion event received from Netatmo: {payload}')
            return updated_homes

        measurement_keys = {
            'temperature', 'co2', 'humidity', 'noise', 'pressure', 'AbsolutePressure',
            'rain', 'sum_rain_1', 'sum_rain_24', 'wind_strength', 'wind_angle',
            'gust_strength', 'gust_angle', 'wind_gust', 'wind_gust_angle'
        }
        status_keys = {'reachable', 'rf_strength', 'wifi_strength', 'battery_state', 'battery_level'}
        sensor_keys = measurement_keys | status_keys

        modules_list = []
        if isinstance(payload.get('modules'), list):
            logging.debug(f'[WEBHOOK EVENT] Found modules in payload["modules"]: {payload["modules"]}')
            modules_list.extend(payload['modules'])
        if isinstance(payload.get('extra_params'), dict) and isinstance(payload['extra_params'].get('modules'), list):
            logging.debug(f'[WEBHOOK EVENT] Found modules in payload["extra_params"]["modules"]: {payload["extra_params"]["modules"]}')
            modules_list.extend(payload['extra_params']['modules'])
        if isinstance(payload.get('data'), dict):
            if isinstance(payload['data'].get('modules'), list):
                logging.debug(f'[WEBHOOK EVENT] Found modules in payload["data"]["modules"]: {payload["data"]["modules"]}')
                modules_list.extend(payload['data']['modules'])
            elif isinstance(payload['data'].get('extra_params'), dict) and isinstance(payload['data']['extra_params'].get('modules'), list):
                logging.debug(f'[WEBHOOK EVENT] Found modules in payload["data"]["extra_params"]["modules"]: {payload["data"]["extra_params"]["modules"]}')
                modules_list.extend(payload['data']['extra_params']['modules'])

        # Handle single-module webhook payload if measurements are directly on payload or extra_params
        if not modules_list:
            candidate = None
            if isinstance(payload.get('extra_params'), dict) and (payload['extra_params'].get('id') or payload.get('module_id') or device_id):
                candidate = dict(payload['extra_params'])
                if 'id' not in candidate:
                    candidate['id'] = payload.get('module_id') or device_id
            elif payload.get('module_id') or device_id:
                if any(k in payload for k in sensor_keys):
                    candidate = dict(payload)
                    candidate['id'] = payload.get('module_id') or device_id
            if candidate:
                logging.debug(f'[WEBHOOK EVENT] Found single module candidate in payload: {candidate}')
                modules_list.append(candidate)

        logging.info(f'[WEBHOOK EVENT] Extracted {len(modules_list)} module item(s) from webhook event')

        updated_inline = False
        has_inline_measurements = False
        for mod in modules_list:
            if not isinstance(mod, dict):
                continue
            mod_id = mod.get('id') or mod.get('_id') or mod.get('module_id')
            if not mod_id:
                logging.debug(f'[WEBHOOK EVENT] Skipping module item without id: {mod}')
                continue
            resolved_home, raw_type = self._resolve_home_and_type(mod_id, home_id, mod.get('type'))
            if not resolved_home:
                logging.warning(f'[WEBHOOK EVENT] Could not resolve home for module {mod_id}')
                continue
            mod_type = self.module_type(raw_type)
            if not mod_type:
                logging.warning(f'[WEBHOOK EVENT] Unknown module category for raw type "{raw_type}" (module {mod_id})')
                continue
            self._ensure_instant_home(resolved_home)
            existing = dict(self.instant_data[resolved_home][mod_type].get(mod_id, {}))
            if isinstance(mod.get('dashboard_data'), dict):
                existing.update(mod['dashboard_data'])
                if any(k in mod['dashboard_data'] for k in measurement_keys):
                    has_inline_measurements = True
            existing.update(mod)
            if any(k in mod for k in measurement_keys):
                has_inline_measurements = True
            if 'ts' not in mod and 'last_seen' not in mod and 'time_utc' not in mod:
                existing['ts'] = event_ts
            elif 'ts' not in existing:
                existing['ts'] = existing.get('last_seen') or existing.get('time_utc') or event_ts
            if 'reachable' not in existing:
                existing['reachable'] = True
            self.instant_data[resolved_home][mod_type][mod_id] = existing
            updated_homes.add(resolved_home)
            updated_inline = True
            logging.info(f'[WEBHOOK EVENT] Updated instant data for {mod_id} ({mod_type}) in home {resolved_home}: {existing}')

        if updated_inline:
            logging.info(
                f'[WEBHOOK EVENT] updated_inline=True, has_inline_measurements={has_inline_measurements}, '
                f'affected homes={updated_homes}'
            )
            for h_id in updated_homes:
                if not has_inline_measurements:
                    logging.info(f'[WEBHOOK EVENT] No inline measurements; fetching instant telemetry via homestatus for home {h_id}...')
                    self.update_weather_info_instant(h_id)
                else:
                    logging.info(f'[WEBHOOK EVENT] Inline measurements present; merging data directly for home {h_id}...')
                    self.merge_data(h_id)
            return updated_homes

        # If webhook notification did not include inline module measurements (e.g. topology_changed or trigger),
        # refresh instant status for the affected home(s).
        logging.info(
            f'[WEBHOOK EVENT] No inline module data matched. Fallback refresh for home_id="{home_id}", '
            f'device_id="{device_id}"'
        )
        if not home_id and device_id:
            home_id, _ = self._resolve_home_and_type(device_id)
            logging.info(f'[WEBHOOK EVENT] Resolved home_id "{home_id}" from device_id "{device_id}"')
        if home_id:
            logging.info(f'[WEBHOOK EVENT] Refreshing homestatus for home {home_id}')
            self.update_weather_info_instant(home_id)
            updated_homes.add(home_id)
        elif hasattr(self, 'weather_in_homes') and self.weather_in_homes:
            logging.info(f'[WEBHOOK EVENT] Refreshing homestatus for all known weather homes: {self.weather_in_homes}')
            for h_id in self.weather_in_homes:
                self.update_weather_info_instant(h_id)
                updated_homes.add(h_id)
        else:
            logging.warning('[WEBHOOK EVENT] Could not identify home or devices to refresh from webhook payload')

        return updated_homes

    def merge_data_str(self, data):
        '''merge_data_str'''
        if data in ('ts', 'time_utc', 'last_seen'):
            data_str = 'time_stamp'
        elif data == 'AbsolutePressure':
            data_str = 'absolute_pressure'
        elif data == 'reachable':
            data_str = 'online'
        elif data == 'wind_strength':
            data_str = 'windstrength'
        elif data == 'wind_angle':
            data_str = 'windangle'
        elif data in ('gust_strength', 'wind_gust'):
            data_str = 'guststrength'
        elif data in ('gust_angle', 'wind_gust_angle'):
            data_str = 'gustangle'
        else:
            data_str = data.lower()
        return data_str

    def merge_data(self, home_id):
        '''Merges/combines cloud data and instant data '''
        try:
            logging.debug('merge_data')
            has_instant = home_id in self.instant_data and bool(self.instant_data[home_id])
            has_cloud = home_id in self.cloud_data and bool(self.cloud_data[home_id])
            if not has_instant and not has_cloud:
                return

            if home_id not in self.weather_data:
                self.weather_data[home_id] = {}

            module_types = set()
            if has_cloud:
                module_types.update(self.cloud_data[home_id].keys())
            if has_instant:
                module_types.update(self.instant_data[home_id].keys())

            for module_type in module_types:
                if not module_type:
                    continue
                if module_type not in self.weather_data[home_id]:
                    self.weather_data[home_id][module_type] = {}

                module_adrs = set()
                if has_cloud and module_type in self.cloud_data[home_id]:
                    module_adrs.update(self.cloud_data[home_id][module_type].keys())
                if has_instant and module_type in self.instant_data[home_id]:
                    module_adrs.update(self.instant_data[home_id][module_type].keys())

                for module_adr in module_adrs:
                    if module_adr not in self.weather_data[home_id][module_type]:
                        self.weather_data[home_id][module_type][module_adr] = {}

                    cloud_mod_adr_data = (
                        self.cloud_data[home_id].get(module_type, {}).get(module_adr, {})
                        if has_cloud else {}
                    )
                    inst_mod_adr_data = (
                        self.instant_data[home_id].get(module_type, {}).get(module_adr, {})
                        if has_instant else {}
                    )

                    cloud_ts = cloud_mod_adr_data.get('time_utc') or cloud_mod_adr_data.get('ts')
                    inst_ts = inst_mod_adr_data.get('ts') or inst_mod_adr_data.get('last_seen') or inst_mod_adr_data.get('time_utc')
                    cloud_ok = bool(cloud_mod_adr_data)
                    inst_ok = bool(inst_mod_adr_data)

                    if cloud_ok and inst_ok:
                        logging.debug('both cloud and instant')
                        if cloud_ts is not None and inst_ts is not None and cloud_ts > inst_ts:
                            first_src, second_src = inst_mod_adr_data, cloud_mod_adr_data
                        else:
                            first_src, second_src = cloud_mod_adr_data, inst_mod_adr_data
                        for data in first_src:
                            data_str = self.merge_data_str(data)
                            self.weather_data[home_id][module_type][module_adr][data_str] = first_src[data]
                        for data in second_src:
                            data_str = self.merge_data_str(data)
                            self.weather_data[home_id][module_type][module_adr][data_str] = second_src[data]
                    elif cloud_ok:
                        for data in cloud_mod_adr_data:
                            data_str = self.merge_data_str(data)
                            self.weather_data[home_id][module_type][module_adr][data_str] = cloud_mod_adr_data[data]
                    elif inst_ok:
                        for data in inst_mod_adr_data:
                            data_str = self.merge_data_str(data)
                            self.weather_data[home_id][module_type][module_adr][data_str] = inst_mod_adr_data[data]
            logging.debug('merge_data complete {}'.format(self.weather_data))
        except Exception as E:
            logging.error('Exception merging data: {} - {}: {} {}'.format(E, self.weather_data, self.instant_data, self.cloud_data))
            
    def get_homes(self):
        '''get_homes'''

        tmp = self.get_homes_info()
        self.weather_in_homes = {}
        for home_id in tmp:
            found = False
            for mod_type in tmp[home_id]['module_types']:
                if mod_type in self._dev_list:
                    found = True
            if found:
                self.weather_in_homes[home_id] = tmp[home_id]
        if not self.weather_in_homes:
            logging.warning('No weather stations found in /homesdata; checking /getstationsdata')
            stations_resp = self._callApi('GET', '/getstationsdata?get_favorites=false')
            if stations_resp and 'body' in stations_resp:
                self.homes_list = self.process_stations_data(stations_resp['body'])
                for home_id in self.homes_list:
                    found = any(
                        mod_type in self._dev_list
                        for mod_type in self.homes_list[home_id]['module_types']
                    )
                    if found:
                        self.weather_in_homes[home_id] = self.homes_list[home_id]
        return self.weather_in_homes

    def get_main_modules(self, home_id):
        '''get_main_modules '''
        tmp = self._get_modules(home_id, self.MAIN_modules)
        logging.debug('get_main_modules {}'.format(tmp))
        return(self._get_modules(home_id, self.MAIN_modules))
    

    def get_indoor_modules(self, home_id):
        '''get_indoor_modules '''
        return(self._get_modules(home_id, self.INDOOR_modules))        


    def get_outdoor_modules(self, home_id):
        '''get_outdoor_modules '''
        return(self._get_modules(home_id, self.OUTDOOR_modules))    
    
    
    def get_rain_modules(self, home_id):
        '''get_rain_modules '''
        return(self._get_modules(home_id,self.RAIN_modules))    


    def get_wind_modules(self, home_id):
        '''get_wind_modules '''
        return(self._get_modules(home_id, self.WIND_modules))    


    def _get_weather_data(self, home_id, dev_id, mod_type):
        '''Get data function'''
        if home_id in self.weather_data:
            if mod_type in self.weather_data[home_id]:
                if dev_id in self.weather_data[home_id][mod_type]:
                    return(self.weather_data[home_id][mod_type][dev_id])
        else:
            logging.warning('No data fouond for {0} {1}'.format(home_id, dev_id))
    '''
    def get_main_module_data(self, home_id, dev_id):
        #Get data from main module
        logging.debug('get_main_module_data')
        #data_list = ['Temperature', 'CO2', 'Humidity', 'Noise', 'Pressure', 'AbsolutePressure', 'min_temp', 'max_temp', 'date_max_temp', 'date_min_temp', 'temp_trend', 'reachable']
        return(self._get_weather_data(home_id, dev_id, 'MAIN'))
    '''    

    def get_module_data(self, module):
        logging.debug('get_indoor_module_data')
        #data_list = ['temperature', 'co2', 'humidity', 'last_seen', 'battery_state', 'ts']
        return(self._get_weather_data(module['home_id'], module['module_id'], module['type']))
               
    '''
    def get_outdoor_module_data(self, home_id, dev_id=None):
        logging.debug('get_outdoor_module_data')
        #data_list = ['temperature', 'co2', 'humidity', 'last_seen', 'battery_state', 'ts']
        return(self._get_weather_data(home_id, dev_id, 'OUTDOOR'))

    def get_rain_module_data(self, home_id, dev_id=None):
        logging.debug('get_rain_module_data')
        #data_list = ['rain', 'sum_rain_1', 'sum_rail_24', 'last_seen', 'battery_state', 'ts']
        return(self._get_weather_data(home_id, dev_id, 'RAIN'))

    def get_wind_module_data(self, home_id, dev_id=None):
        logging.debug('get_wind_module_data')
        #data_list = ['wind_strength', 'wind_angle', 'wind+gust', 'wind_gust_angle', 'last_seen', 'battery_state', 'ts']
        return(self._get_weather_data(home_id, dev_id, 'WIND'))
    '''

    def get_temperature_C(self, module):
        try:
            logging.debug('get_temperature_C {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['temperature'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['temperature'])       
        except Exception as e:
            logging.error('get_temperature_C exception; {}'.format(e))
            return(None)
    def get_max_temperature_C (self, module):
        try:
            logging.debug('get_max_temperature_C {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['max_temp'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['max_temp'])       
        except Exception as e:
            logging.error('get_max_temperature_C exception; {}'.format(e))
            return(None)

    def get_min_temperature_C(self, module):
        try:
            logging.debug('get_min_temperature_C {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['min_temp'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['min_temp'])       
        except Exception as e:
            logging.error('get_min_temperature_C exception; {}'.format(e))
            return(None)

    def get_co2(self, module):
        try:
            logging.debug('get_co2 {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['co2'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['co2'])       
        except Exception as e:
            logging.error('get_co2 exception; {}'.format(e))
            return(None)

    def get_noise(self, module):
        try:
            logging.debug('get_noise {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['noise'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['noise'])       
        except Exception as e:
            logging.error('get_co2 exception; {}'.format(e))
            return(None)
        
    def get_humidity(self, module):
        try:
            logging.debug('get_humidity {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['humidity'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['humidity'])       
        except Exception as e:
            logging.error('get_humidity exception; {}'.format(e))
            return(None)

    def get_pressure(self, module):
        try:
            logging.debug('get_pressure {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['pressure'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['pressure'])       
        except Exception as e:
            logging.error('get_pressure exception; {}'.format(e))
            return(None)

    def get_abs_pressure(self, module):
        try:
            logging.debug('get_abs_pressure {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['absolute_pressure'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['absolute_pressure'])       
        except Exception as e:
            logging.error('absolute_pressure exception; {}'.format(e))
            return(None)        

    def get_time_stamp(self, module):
        try:
            logging.debug('get_time_stamp {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['time_stamp'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['time_stamp'])       
        except Exception as e:
            logging.error('get_time_stamp exception: {}'.format(e))
            return(None)        
             
    def get_time_since_time_stamp_min(self, module):
        try:
            unix_timestamp = datetime.now(timezone.utc).timestamp()
            meas_time = self.get_time_stamp(module)
            if meas_time is None:
                return 0
            delay = max(0, unix_timestamp - meas_time)
            return round(delay / 60, 2)  # delay min
        except Exception as e:
            logging.error('get_time_since_time_stamp_min exception: {}'.format(e))
            return 0

    def get_temp_trend(self, module):
        try:
            trend = self.weather_data[module['home_id']][module['type']][module['module_id']]['temp_trend']
            return(trend)       
        except Exception as e:
            logging.error('get_temp_trend exception; {}'.format(e))
            return( None)
    
    def get_hum_trend(self, module):
        try:
            trend = self.weather_data[module['home_id']][module['type']][module['module_id']]['pressure_trend']
   
        except Exception as e:
            logging.error('get_hum_trend exception; {}'.format(e))
            return( None, None)
        

    def get_rain(self, module):
        try:
            logging.debug('get_rain {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['rain'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['rain'])       
        except Exception as e:
            logging.error('get_rain exception; {}'.format(e))
            return(None)      

    def get_rain_1hour(self, module):
        try:
            logging.debug('get_rain_1hour {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['sum_rain_1'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['sum_rain_1'])       
        except Exception as e:
            logging.error('get_rain_1hour {}'.format(e))
            return(None)  
    
    def get_rain_24hours(self, module):
        try:
            logging.debug('get_rain_24hours {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['sum_rain_24'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['sum_rain_24'])       
        except Exception as e:
            logging.error('get_rain_24hours exception; {}'.format(e))
            return(None)  

    def get_wind_angle(self, module):
        try:
            logging.debug('get_wind_angle {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['windangle'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['windangle'])       
        except Exception as e:
            logging.error('get_wind_angle exception; {}'.format(e))
            return(None)  

    def get_wind_strength(self, module):
        try:
            logging.debug('get_wind_strength {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['windstrength'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['windstrength'])       
        except Exception as e:
            logging.error('get_wind_strength exception; {}'.format(e))
            return(None)  

    def get_gust_angle(self, module):
        try:
            logging.debug('get_wind_angle {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['gustangle'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['gustangle'])       
        except Exception as e:
            logging.error('get_wind_angle exception; {}'.format(e))
            return(None)  

    def get_gust_strength(self, module):
        try:
            logging.debug('get_wind_strength {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['guststrength'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['guststrength'])       
        except Exception as e:
            logging.error('get_wind_strength exception; {}'.format(e))
            return(None)  
        
    def get_max_wind_angle(self, module):
        try:
            logging.debug('get_wind_angle {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['max_wind_angle'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['max_wind_angle'])       
        except Exception as e:
            logging.error('get_wind_angle exception; {}'.format(e))
            return(None)  

    def get_max_wind_strength(self, module):
        try:
            logging.debug('get_wind_strength {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['max_wind_str'],module['home_id'], module['type'], module['module_id'] ))
            return(self.weather_data[module['home_id']][module['type']][module['module_id']]['max_wind_str'])       
        except Exception as e:
            logging.error('get_wind_strength exception; {}'.format(e))
            return(None)          

    def get_battery_info(self, module):
        try:
            mod_data = self.weather_data.get(module['home_id'], {}).get(module['type'], {}).get(module['module_id'], {})
            bat1 = mod_data.get('battery_state')
            bat2 = mod_data.get('battery_level')
            return (bat1, bat2)
        except Exception as e:
            logging.error('get_battery_info exception: {}'.format(e))
            return (None, None)
        
    def get_rf_info(self, module):
        try:
            rf1 = None
            rf2 = None
            mod_data = self.weather_data.get(module['home_id'], {}).get(module['type'], {}).get(module['module_id'], {})
            if 'rf_state' in mod_data:
                rf1 = mod_data['rf_state']
            if 'wifi_state' in mod_data:
                rf1 = mod_data['wifi_state']
            if 'rf_strength' in mod_data and mod_data['rf_strength'] is not None:
                rf2 = -abs(mod_data['rf_strength'])
            if 'wifi_strength' in mod_data and mod_data['wifi_strength'] is not None:
                rf2 = -abs(mod_data['wifi_strength'])
            return (rf1, rf2)
        except Exception as e:
            logging.error('get_rf_info exception; {}'.format(e))
            return (None, None)

    def get_online(self, module):
        try:
            #logging.debug('module {} '.format(module) )
            #logging.debug('module data1: {}'.format(self.weather_data))
            #logging.debug('module data2: {} - {} - {}'.format(module['home_id'], module['type'],module['module_id']))
            #logging.debug('module data3: {}'.format(self.weather_data[module['home_id']]))
            #logging.debug('module data4: {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]))
            #logging.debug('get_online {} {} {} {}'.format(self.weather_data[module['home_id']][module['type']][module['module_id']]['online'],module['home_id'], module['type'], module['module_id'] ))
            if 'online' in self.weather_data[module['home_id']][module['type']][module['module_id']]:    
                return(self.weather_data[module['home_id']][module['type']][module['module_id']]['online'])
            else:
                return(False)      
        except Exception as e:
            logging.warning('No online data exists - Assume off line : {} - {}'.format(e, module))
            return(False)


