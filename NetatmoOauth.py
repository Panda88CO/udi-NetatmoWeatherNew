
#!/usr/bin/env python3

### Your external service class
'''
Your external service class can be named anything you want, and the recommended location would be the lib folder.
It would look like this:

External service sample code
Copyright (C) 2023 Universal Devices

MIT License
'''
import requests
import time
import json
import urllib.parse
#from udi_interface import LOGGER, Custom
#from oauth import OAuth
try:
    from udi_interface import LOGGER, Custom, OAuth
    logging = LOGGER
    Custom = Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)



# Implements the API calls to your external service
# It inherits the OAuth class
class NetatmoCloud(OAuth):
    yourApiEndpoint = 'https://api.netatmo.com/api'

    def __init__(self, polyglot, scope):
        super().__init__(polyglot)
        logging.info('OAuth initializing')
        self.poly = polyglot
        self.scope = scope
        self.customParameters = Custom(self.poly, 'customparams')
        #self.scope_str = None
        self.apiEndpoint = 'https://api.netatmo.com'
        self.client_ID = None
        self.client_SECRET = None
        self.handleCustomParamsDone = False
        #self.customerDataHandlerDone = False
        self.customNsHandlerDone = False
        self.temp_unit = 'C'

        self.scopeList = ['read_station', 'read_magellan', 'write_magellan', 'read_bubendorff', 'write_bubendorff', 'read_smarther', 'write_smarther', 'read_thermostat','write_thermostat', 'read+_camera', 'write_camera', 'access_camera', 'read_boorbell', 'access_doorbell',
             'read_mx', 'write_mx', 'read_presence', 'write_presence', 'access_presence', 'read_homecoach', 'read_carbonmonoxidedetector', 'read_smokedetector', 'read_mhs1', 'write_mhs1']
        
        self.poly = polyglot
        #self.customParameters= Custom(polyglot, 'customparams')
        #self.Notices = Custom(self.poly, 'notices')

        logging.info('External service connectivity initialized...')
        #logging.debug('oauth : {}'.format(self.oauthConfig))

        time.sleep(1)
        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customParams to complete - getAccessToken')
        #    time.sleep(0.2)
        # self.getAccessToken()
    
    # The OAuth class needs to be hooked to these 3 handlers
    def customDataHandler(self, data):
        logging.debug('customDataHandler called')
        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customDataHandler to complete')
        #    time.sleep(1)
        super().customDataHandler(data)
        self.customDataHandlerDone = True
        logging.debug('customDataHandler Finished')

    def customNsHandler(self, key, data):
        logging.debug('customNsHandler called')
        #while not self.customParamsDone():
        #    logging.debug('Waiting for customNsHandler to complete')
        #    time.sleep(1)
        #self.updateOauthConfig()
        super().customNsHandler(key, data)
        self.customNsHandlerDone = True
        logging.debug('customNsHandler Finished')

    def oauthHandler(self, token):
        logging.debug('oauthHandler called')
        while not (self.customParamsDone() and self.customNsDone()):
            logging.debug('Waiting for oauthHandler to complete')
            time.sleep(5)
        super().oauthHandler(token)
        #self.customOauthHandlerDone = True
        logging.debug('oauthHandler Finished')

    def customNsDone(self):
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )

    def customParamsDone(self):
        return(self.handleCustomParamsDone)
    #def refresh_token(self):
    #    logging.debug('checking token for refresh')
        

    # Your service may need to access custom params as well...
    
    def main_module_enabled(self, node_name):
        logging.debug('main_module_enabled called {}'.format(node_name))
        if node_name in self.customParameters:           
            return(int(self.customParameters[node_name]) == 1)
        else:
            self.customParameters[node_name] = 1 #add and enable by default
            self.poly.Notices['home_id'] = 'Check config to select which home/modules should be used (1 - used, 0 - not used) - then restart'
            return(True)

                
    def customParamsHandler(self, userParams):
        self.customParameters.load(userParams)
        logging.debug('customParamsHandler called {}'.format(userParams))
        client_ok = False
        secret_ok = False
        oauthSettingsUpdate = {}
        invalid_client_ids = {'', 'enter client_id', 'enter clientid', 'client_id', 'clientid'}
        invalid_client_secrets = {'', 'enter client_secret', 'enter clientsecret', 'client_secret', 'clientsecret'}

        client_id_val = userParams.get('clientID') if 'clientID' in userParams else userParams.get('ClientID')
        if client_id_val is None:
            client_id_val = (
                self.customParameters['clientID']
                if 'clientID' in self.customParameters
                else (self.customParameters['ClientID'] if 'ClientID' in self.customParameters else None)
            )
        if client_id_val is not None:
            cleaned_id = str(client_id_val).strip()
            if cleaned_id.lower() not in invalid_client_ids and not cleaned_id.lower().startswith('enter '):
                self.client_ID = cleaned_id
                oauthSettingsUpdate['client_id'] = cleaned_id
                client_ok = True
            else:
                logging.warning(f'clientID is still set to placeholder ({cleaned_id!r}); please enter a valid clientID')
                self.client_ID = None
        else:
            logging.warning('No clientID found')
            self.customParameters['clientID'] = 'Enter clientID'
            self.client_ID = None

        client_secret_val = (
            userParams.get('clientSecret')
            if 'clientSecret' in userParams
            else userParams.get('ClientSecret')
        )
        if client_secret_val is None:
            client_secret_val = (
                self.customParameters['clientSecret']
                if 'clientSecret' in self.customParameters
                else (self.customParameters['ClientSecret'] if 'ClientSecret' in self.customParameters else None)
            )
        if client_secret_val is not None:
            cleaned_secret = str(client_secret_val).strip()
            if cleaned_secret.lower() not in invalid_client_secrets and not cleaned_secret.lower().startswith('enter '):
                self.client_SECRET = cleaned_secret
                oauthSettingsUpdate['client_secret'] = cleaned_secret
                secret_ok = True
            else:
                logging.warning('clientSecret is still set to placeholder; please enter a valid clientSecret')
                self.client_SECRET = None
        else:
            logging.warning('No clientSecret found')
            self.customParameters['clientSecret'] = 'Enter clientSecret'
            self.client_SECRET = None

        if not client_ok or not secret_ok:
            self.handleCustomParamsDone = False
            self.poly.Notices['client'] = 'Please enter valid clientID and clientSecret - then restart'

        if "TEMP_UNIT" in self.customParameters and self.customParameters['TEMP_UNIT']:
            self.temp_unit = str(self.customParameters['TEMP_UNIT'])[0].upper()
        else:
            self.temp_unit = 'C'
            self.customParameters['TEMP_UNIT'] = 'C'

        oauthSettingsUpdate['scope'] = self.scope
        oauthSettingsUpdate['auth_endpoint'] = 'https://api.netatmo.com/oauth2/authorize'
        oauthSettingsUpdate['token_endpoint'] = 'https://api.netatmo.com/oauth2/token'
        oauthSettingsUpdate['addRedirect'] = True
        self.updateOauthSettings(oauthSettingsUpdate)
        if client_ok and secret_ok:
            default_webhook_url = self.get_portal_webhook_url()
            if 'WEBHOOK_URL' not in self.customParameters or not self.customParameters['WEBHOOK_URL']:
                if default_webhook_url:
                    self.customParameters['WEBHOOK_URL'] = default_webhook_url
            self.handleCustomParamsDone = True
            if 'client' in self.poly.Notices:
                self.poly.Notices.delete('client')

        #self.updateOauthConfig()
        #self.myParamBoolean = ('myParam' in self.customParametersand self.customParameters['myParam'].lower() == 'true')
        #logging.info(f"My param boolean: { self.myParamBoolean }")
    

    def add_to_parameters(self,  key, value):
        '''add_to_parameters'''
        self.customParameters[key] = value

    def check_parameters(self, key, value):
        '''check_parameters'''
        if key in self.customParameters:
            return(self.customParameters[key]  == value)
        else:
            return(False)
    
    def authendicated(self):
        try:
            logging.debug('authendicated - {}'.format(self.getOauthSettings()))
            self.getAccessToken()
            return(True)
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            #self.poly.Notices['auth'] = 'Please initiate authentication'
            return (False)
        

    def setOauthScope(self, scope):
        oauthSettingsUpdate = {}
        logging.debug('Set Scope to {}'.format(scope))
        oauthSettingsUpdate['scope'] = str(scope)
        self.updateOauthSettings(oauthSettingsUpdate)
    
    def setOauthName(self, name):
        oauthSettingsUpdate = {} 
        logging.debug('Set name to {}'.format(name))
        oauthSettingsUpdate['name'] = str(name)
        self.updateOauthSettings(oauthSettingsUpdate)
    
    '''
    def _insert_refreshToken(self, refresh_token, clientId, clientSecret):
        data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': clientId,
                'client_secret':  clientSecret
                }
        try:
            response = requests.post('https://api.netatmo.com/oauth2/token' , data=data)
            response.raise_for_status()
            token = response.json()
            logging.info('Refreshing tokens successful')
            logging.debug(f"Token refresh result [{ type(token) }]: { token }")
            self._saveToken(token)
            return('Success')
          
        except requests.exceptions.HTTPError as error:
            logging.error(f"Failed to refresh  token: { error }")
            return(None)
            # NOTE: If refresh tokens fails, we keep the existing tokens available.
    '''

    # Call your external service API
    def _callApi(self, method='GET', url=None, body=None):
        # When calling an API, get the access token (it will be refreshed if necessary)
        try:
            accessToken = self.getAccessToken()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            return None
        if accessToken is None:
            logging.error('Access token is not available')
            return None

        if url is None:
            logging.error('url is required')
            return None

        completeUrl = self.yourApiEndpoint + url

        headers = {
            'Authorization': f"Bearer { accessToken }"
        }

        if method in ['PATCH'] and body is None:
            logging.error(f"body is required when using { method } { completeUrl }")
        logging.debug(' call info url={}, header= {}, body = {}'.format(completeUrl, headers, body))

        max_attempts = 3
        retry_statuses = {429, 500, 502, 503, 504}
        for attempt in range(1, max_attempts + 1):
            try:
                if method == 'GET':
                    response = requests.get(completeUrl, headers=headers, timeout=15)
                elif method == 'DELETE':
                    response = requests.delete(completeUrl, headers=headers, timeout=15)
                elif method == 'PATCH':
                    response = requests.patch(completeUrl, headers=headers, json=body, timeout=15)
                elif method == 'POST':
                    if body is not None:
                        response = requests.post(completeUrl, headers=headers, json=body, timeout=15)
                    else:
                        response = requests.post(completeUrl, headers=headers, timeout=15)
                elif method == 'PUT':
                    response = requests.put(completeUrl, headers=headers, timeout=15)

                if response.status_code in retry_statuses and attempt < max_attempts:
                    delay = 1.5 * attempt
                    logging.warning(
                        f"Call {method} {completeUrl} returned HTTP {response.status_code} "
                        f"(attempt {attempt}/{max_attempts}); retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                try:
                    return response.json()
                except requests.exceptions.JSONDecodeError:
                    return response.text

            except requests.exceptions.HTTPError as error:
                status_code = error.response.status_code if error.response is not None else None
                if status_code in retry_statuses and attempt < max_attempts:
                    delay = 1.5 * attempt
                    logging.warning(
                        f"Call {method} {completeUrl} failed with HTTP {status_code} "
                        f"(attempt {attempt}/{max_attempts}); retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                logging.error(f"Call { method } { completeUrl } failed: { error }")
                return None
            except requests.exceptions.RequestException as error:
                if attempt < max_attempts:
                    delay = 1.5 * attempt
                    logging.warning(
                        f"Request {method} {completeUrl} failed ({error}) "
                        f"(attempt {attempt}/{max_attempts}); retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                logging.error(f"Request { method } { completeUrl } failed: { error }")
                return None
        return None

    def get_portal_webhook_url(self):
        try:
            config = self.poly.getConfig()
            uuid = config.get('uuid')
            slot = config.get('profileNum')
            if uuid and slot is not None:
                return f"https://my.isy.io/api/eisy/pg3/webhook/noresponse/{uuid}/{slot}"
        except Exception as e:
            logging.error(f"Error building portal webhook URL: {e}")
        return None

    def get_webhook_url(self):
        if 'WEBHOOK_URL' in self.customParameters and self.customParameters['WEBHOOK_URL']:
            url = str(self.customParameters['WEBHOOK_URL']).strip()
            if url:
                return url
        return self.get_portal_webhook_url()

    def testWebhook(self, body):
        config = self.poly.getConfig()
        uuid = config['uuid']
        slot = config['profileNum']
        headers = {
            "Content-Type": "application/json"
        }
        completeUrl = f"https://my.isy.io/api/eisy/pg3/webhook/noresponse/{uuid}/{slot}"
        logging.debug(f' Calling { completeUrl } with body: { body }')
        try:
            response = requests.post(completeUrl, headers=headers, json=body, timeout=5)
            response.raise_for_status()
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.text
        except requests.exceptions.HTTPError as error:
            logging.error(f"Call post { completeUrl } failed: { error }")
            if error.response is not None and error.response.status_code == 503:
                logging.error('Error 503: The MQTT connection to the IoX for this UUID is not online - check that remote connections is active in the ISY Portal on the PG3 -> Remote Connection page.')
                logging.error('Make sure this work at https://my.isy.io -> Select Tool | PG3 | Remote connection. It should read "Current status: Connected". Note that it may take up to a minute after switching it on to take effect.')
            elif error.response is not None and error.response.status_code == 423:
                logging.error('Error 423: The UUID is not found in your portal account or does not have an active license')
            raise error

    def add_webhook(self, webhook_url=None):
        logging.debug('add_webhook called')
        if webhook_url is None:
            webhook_url = self.get_webhook_url()
        if not webhook_url:
            logging.error('No webhook URL available to register with Netatmo')
            return False
        encoded_url = urllib.parse.quote_plus(webhook_url)
        api_str = f'/addwebhook?url={encoded_url}&app_type=app_station'
        res = self._callApi('POST', api_str)
        if res is None:
            api_str_fallback = f'/addwebhook?url={encoded_url}'
            res = self._callApi('POST', api_str_fallback)
        if isinstance(res, dict) and res.get('status') == 'ok':
            logging.info(f'Successfully registered Netatmo webhook: {webhook_url}')
            return True
        logging.warning(f'Netatmo addwebhook response: {res}')
        return res is not None

    def drop_webhook(self):
        logging.debug('drop_webhook called')
        res = self._callApi('POST', '/dropwebhook?app_type=app_station')
        if res is None:
            res = self._callApi('POST', '/dropwebhook')
        if isinstance(res, dict) and res.get('status') == 'ok':
            logging.info('Successfully dropped Netatmo webhook')
            return True
        logging.debug(f'Netatmo dropwebhook response: {res}')
        return False

    # Then implement your service specific APIs
    '''
    def getAllDevices(self):
        return self._callApi(url='/devices')

    def unsubscribe(self):
        return self._callApi(method='DELETE', url='/subscription')

    def getUserInfo(self):
        return self._callApi(url='/user/info')
    '''
    '''
    def updateOauthConfig(self):
        logging.debug('updateOauthConfig')
        logging.debug(' {} {} {}'.format(self.client_ID,self.client_SECRET, self.scope_str  ))
        self.addOauthParameter('client_id',self.client_ID )
        self.addOauthParameter('client_secret',self.client_SECRET )
        self.addOauthParameter('scope','read_station' )
        #self.addOauthParameter('state','dette er en test' )
        #self.addOauthParameter('redirect_uri','https://my.isy/io/api/cloudlink/redirect' )
        self.addOauthParameter('name','Netatmo Weather' )
        self.addOauthParameter('cloudlink', True )
        self.addOauthParameter('addRedirect', True )
        logging.debug('updateOauthConfig = {}'.format(self.oauthConfig))
    '''
### Main node server code

    #def set_temp_unit(self, value):
    #    self.temp_unit = value

    
    def get_weather_info(self):
        logging.debug('get_weather_info')
        api_str = '/getstationsdata'
        res = self._callApi('GET', api_str )
        logging.debug(res)

    def get_weather_info2(self):
        logging.debug('get_weather_info')
        api_str = '/homestatus'
        res = self._callApi('GET', api_str )
        logging.debug(res)

    def process_homes_data(self, net_system):
        homes_list = {}
        if not net_system or 'homes' not in net_system:
            return homes_list
        for home in range(0, len(net_system['homes'])):
            tmp = net_system['homes'][home]
            homes_list[tmp['id']] = {}
            homes_list[tmp['id']]['name'] = tmp.get('name', tmp['id'])
            homes_list[tmp['id']]['modules'] = {}
            homes_list[tmp['id']]['module_types'] = []
            if 'modules' in tmp:
                for mod in range(0, len(tmp['modules'])):
                    homes_list[tmp['id']]['modules'][tmp['modules'][mod]['id']] = tmp['modules'][mod]
                    homes_list[tmp['id']]['module_types'].append(tmp['modules'][mod]['type'])
        return homes_list

    def process_stations_data(self, stations_body):
        homes_list = {}
        if not stations_body or 'devices' not in stations_body:
            return homes_list
        for dev in stations_body.get('devices', []):
            dev_id = dev.get('_id') or dev.get('id')
            if not dev_id:
                continue
            home_id = dev.get('home_id') or dev_id
            main_name = dev.get('module_name') or dev.get('name') or dev_id
            home_name = dev.get('home_name')
            if not home_name:
                station_name = dev.get('station_name', home_id)
                suffix = f' ({main_name})'
                if isinstance(station_name, str) and station_name.endswith(suffix):
                    home_name = station_name[:-len(suffix)]
                else:
                    home_name = station_name
            if home_id not in homes_list:
                homes_list[home_id] = {
                    'name': home_name,
                    'modules': {},
                    'module_types': [],
                }
            bridged_ids = []
            for sub in dev.get('modules', []):
                sub_id = sub.get('_id') or sub.get('id')
                if not sub_id:
                    continue
                sub_type = sub.get('type')
                sub_name = sub.get('module_name') or sub.get('name') or sub_id
                bridged_ids.append(sub_id)
                homes_list[home_id]['modules'][sub_id] = {
                    'id': sub_id,
                    'type': sub_type,
                    'name': sub_name,
                    'bridge': dev_id,
                }
                if sub_type:
                    homes_list[home_id]['module_types'].append(sub_type)
            main_type = dev.get('type', 'NAMain')
            homes_list[home_id]['modules'][dev_id] = {
                'id': dev_id,
                'type': main_type,
                'name': main_name,
                'modules_bridged': bridged_ids,
            }
            homes_list[home_id]['module_types'].append(main_type)
        return homes_list

    def get_homes_info(self):
        logging.debug('get_home_info')
        api_str = '/homesdata'
        temp = self._callApi('GET', api_str)
        if temp and 'body' in temp:
            self.netatmo_systems = temp['body']
            logging.debug(self.netatmo_systems)
            self.homes_list = self.process_homes_data(self.netatmo_systems)
            if self.homes_list:
                return self.homes_list
        logging.warning('Falling back to /getstationsdata to discover weather stations')
        stations_resp = self._callApi('GET', '/getstationsdata?get_favorites=false')
        if stations_resp and 'body' in stations_resp:
            self.netatmo_systems = stations_resp['body']
            self.homes_list = self.process_stations_data(self.netatmo_systems)
            return self.homes_list
        self.homes_list = {}
        return self.homes_list

    def get_home_status(self, home_id):
        status = {}
        logging.debug('get_home_status')
        try:
            if home_id:
                home_id_str = urllib.parse.quote_plus(home_id)
                api_str = '/homestatus?home_id=' + str(home_id_str)
            else:
                return None

            tmp = self._callApi('GET', api_str)
            if tmp and 'body' in tmp:
                meas_time = int(tmp.get('time_server', int(time.time())))
                tmp_body = tmp['body']
                if 'errors' not in tmp_body and 'home' in tmp_body:
                    home_data = tmp_body['home']
                    status[home_id] = home_id
                    if 'modules' in home_data:
                        status['modules'] = {}
                        status['module_types'] = []
                        for mod in range(0, len(home_data['modules'])):
                            mod_entry = dict(home_data['modules'][mod])
                            if 'ts' not in mod_entry:
                                mod_entry['ts'] = mod_entry.get('last_seen', meas_time)
                            if 'reachable' not in mod_entry:
                                mod_entry['reachable'] = True
                            status['modules'][mod_entry['id']] = mod_entry
                            status['module_types'].append(mod_entry['type'])
                    logging.debug(status)
                else:
                    status['error'] = tmp_body.get('errors') or tmp_body.get('error')

                return status
            return None
        except Exception as e:
            logging.error('Error get home status : {}'.format(e))
            return None

    def get_modules(self, home_id):
        '''get_modules'''
        logging.debug('get_modules')
        if home_id in self.homes_list:
            # Find relevan modules
            return(self.homes_list[home_id]['modules'])
        
    def get_module_types(self, home_id):
        '''get_module_types'''
        if home_id in self.homes_list:
            return(self.homes_list[home_id]['module_types'])

    def get_home_name(self, home_id):
        '''get_home_name'''
        if home_id in self.homes_list:
            return(self.homes_list[home_id]['name'])

    def get_modules_present(self, home_id):
        '''get_modules_present'''
        logging.debug('get_modules_present')
        modules = {}
        if home_id in self.homes_list:
            for tmp in range(0,len(self.homes_list[home_id]['modules'])):
                modules[tmp[id]] = tmp
        return(modules)
    
    def get_sub_modules(self, home_id, main_module_id):
        '''get_sub_modules'''
        logging.debug('get_sub_modules')
        if home_id in  self.homes_list:
            if main_module_id in self.homes_list[home_id]['modules']:
                if 'modules_bridged' in self.homes_list[home_id]['modules'][main_module_id]:
                    return(self.homes_list[home_id]['modules'][main_module_id]['modules_bridged'])

    def get_module_info(self, home_id, module_id):
        '''get_module_info'''
        logging.debug('get_module_info')
        if home_id in  self.homes_list:
            if module_id in self.homes_list[home_id]['modules']:
                return(self.homes_list[home_id]['modules'][module_id])


    def _get_modules(self, home_id, mod_type_lst):
        '''get list of weather modules of type attached to house_id'''
        try:
            mod_dict = {}
            if home_id in self.homes_list:
               for module in self.homes_list[home_id]['modules']:
                    if self.homes_list[home_id]['modules'][module]['type'] in mod_type_lst:
                        mod_dict[module] = {}
                        if 'name' in  self.homes_list[home_id]['modules'][module]:
                            mod_dict[module]['name'] = self.homes_list[home_id]['modules'][module]['name']
                        else:
                            mod_dict[module]['name'] = self.homes_list[home_id]['modules'][module]['id']
                    


                    
            else:
                logging.error('No data found for {} {}'.format(home_id, mod_type_lst))
            return(mod_dict)
    
        except Exception as e:
            logging.error('Exception : {}'.format(e))
            return(None)