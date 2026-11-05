#!/usr/bin/env python3

"""
Polyglot v3 node server
Copyright (C) 2023 Universal Devices

MIT License
"""

import time
import json
import traceback
import re
import sys
import threading
from threading import Thread
from queue import Queue, Empty

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

from NetatmoWeather import NetatmoWeather
from udiNetatmoWeatherMain import udiNetatmoWeatherMain

version = '0.2.0'


class NetatmoController(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name):
        super(NetatmoController, self).__init__(polyglot, primary, address, name)
        logging.debug('NetatmoController Initializing')
        logging.setLevel(10)
        self.poly = polyglot

        self.accessTokenEn = True
        self.accessToken = None
        self.nodeDefineDone = False
        self.configDone = False
        self.name = name
        self.primary = primary
        self.address = address
        self.temp_unit = 0
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.myNetatmo = NetatmoWeather(self.poly)
        self.hb = 0
        self.webhookTestTimeoutSeconds = 5
        self.webhookSuccess = 'Unknown'
        self.webhookTimer = None
        self.webhook_registered = False
        self.Notices = Custom(self.poly, 'notices')
        self.n_queue = []
        self.homes_list = []

        self.msg_queue = Queue()
        self.stop_processing_messages = False
        self.message_thread = Thread(target=self.process_message, daemon=True)

        self.poly.subscribe(self.poly.STOP, self.stopHandler)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.myNetatmo.customParamsHandler)
        self.poly.subscribe(self.poly.CUSTOMNS, self.myNetatmo.customNsHandler)
        self.poly.subscribe(self.poly.OAUTH, self.myNetatmo.oauthHandler)
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.subscribe(self.poly.WEBHOOK, self.webhook)

        self.poly.addNode(self)
        self.node = self.poly.getNode(self.address)
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.poly.updateProfile()
        self.poly.ready()

    def init_webhook(self):
        logging.debug('init_webhook called')
        self.poly.webhookStart({'name': 'NetatmoWeather'})
        time.sleep(2)

    def webhook_test(self, param=None):
        logging.debug(f'webhook_test called {param}')
        body = {'event': 'webhook-test', 'data': {'type': 'test', 'description': 'webhook test'}}
        try:
            self.webhookSuccess = 'Unknown'
            self.node.setDriver('GV30', 1, True, True)
            self.myNetatmo.testWebhook(body)
            self.webhookTimer = threading.Timer(self.webhookTestTimeoutSeconds, self.webhookTimeout)
            self.webhookTimer.start()
        except Exception as e:
            logging.error(f'Error in webhook_test: {e}')
            self.node.setDriver('GV30', 4, True, True)
            self.webhookSuccess = 'Failure'

    def webhookTimeout(self):
        logging.error('Webhook test timed out - Please verify your setup for receiving webhook events.')
        self.node.setDriver('GV30', 3, True, True)
        self.webhookSuccess = 'Timeout'

    def activate(self):
        logging.info('Webhook was invoked and the program has received it')
        if self.webhookTimer is not None:
            self.webhookTimer.cancel()
        self.node.setDriver('GV30', 2, True, True)
        self.webhookSuccess = 'Success'
        if 'webhook' in self.poly.Notices:
            self.poly.Notices.delete('webhook')

    def webhook(self, data):
        logging.info(f'webhook called with data: {data}')
        if data is not None:
            payload = data
            if isinstance(payload, dict) and 'body' in payload:
                body_data = payload['body']
                if isinstance(body_data, str):
                    try:
                        payload = json.loads(body_data)
                    except Exception:
                        payload = data
                elif isinstance(body_data, dict):
                    payload = body_data
            elif isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    return

            if isinstance(payload, dict) and payload.get('event') == 'webhook-test':
                logging.info('Webhook test received!')
                self.activate()
                return

            self.insert_message(payload)

    def insert_message(self, message):
        self.msg_queue.put(message)

    def process_message(self):
        logging.info('Starting Netatmo webhook message processor')
        while not self.stop_processing_messages:
            try:
                message = self.msg_queue.get(timeout=5)
                if message is not None:
                    self._handle_webhook_message(message)
            except Empty:
                continue
            except Exception as e:
                logging.error(f'Error processing webhook message: {e}')

    def _handle_webhook_message(self, payload):
        logging.debug(f'Handling Netatmo webhook payload: {payload}')
        self.node.setDriver('GV29', 1, True, True)
        updated_homes = self.myNetatmo.process_webhook_data(payload)
        if self.nodeDefineDone and updated_homes:
            nodes = self.poly.nodes()
            for nde in nodes:
                if nde.address != 'controller':
                    nde.updateISYdrivers()
       

    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    def getValidName(self, name):
        name = bytes(name, 'utf-8').decode('utf-8','ignore')
        return re.sub(r"[^A-Za-z0-9_ ]", "", name)

    # remove all illegal characters from node address
    def getValidAddress(self, name):
        name = bytes(name, 'utf-8').decode('utf-8','ignore')
        tmp = re.sub(r"[^A-Za-z0-9_]", "", name.lower())
        logging.debug('getValidAddress {}'.format(tmp))
        return tmp[:14]
    

    def convert_temp_unit(self, tempStr):
        if tempStr.capitalize()[:1] == 'F':
            return(1)
        elif tempStr.capitalize()[:1] == 'C':
            return(0)
   
    def heartbeat(self):
        logging.debug('heartbeat: ' + str(self.hb))
        self.node.setDriver('ST', 1)
        if self.hb == 0:
            self.reportCmd('DON',2)
            self.hb = 1
        else:
            self.reportCmd('DOF',2)
            self.hb = 0

        

    def start(self):
        logging.info('Executing start')
        self.init_webhook()

        self.poly.Notices['webhook'] = 'Checking webhook connection'
        self.webhook_test()
        time.sleep(2)
        test_time = 0
        while self.webhookSuccess == 'Unknown' and test_time < self.webhookTestTimeoutSeconds:
            logging.debug(f'Waiting for webhook test to complete ({self.webhookSuccess})')
            time.sleep(1)
            test_time += 1
        if self.webhookSuccess != 'Success':
            logging.error('Webhook test failed - no data will be received')
            self.poly.Notices['webhook'] = 'Webhook test failed - no data will be received - check node documentation on how to open external access to the eISY/Polisy'
            self.node.setDriver('GV29', 0, True, True)
        elif 'webhook' in self.poly.Notices:
            self.poly.Notices.delete('webhook')

        while not (self.configDone and self.myNetatmo.customParamsDone() and self.myNetatmo.customNsDone()):
            time.sleep(2)
            logging.debug('Waiting for config to complete {} {} {}'.format(self.configDone, self.myNetatmo.customParamsDone(), self.myNetatmo.customNsDone()))

        while not self.myNetatmo.authendicated():
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            time.sleep(5)

        time.sleep(1)
        if 'auth' in self.poly.Notices:
            self.poly.Notices.delete('auth')

        self.home_ids = self.myNetatmo.get_homes()
        if self.home_ids:
            self.node.setDriver('ST', 1, True, True)

        self.temp_unit = self.convert_temp_unit(self.myNetatmo.temp_unit)
        logging.debug('TEMP_UNIT: {}'.format(self.temp_unit))

        while not (self.myNetatmo.customParamsDone() and self.myNetatmo.customNsDone() and self.configDone):
            logging.info('Waiting for configuration to complete')
            time.sleep(1)

        if self.webhookSuccess == 'Success':
            self.webhook_registered = self.myNetatmo.add_webhook()
            self.node.setDriver('GV29', 1 if self.webhook_registered else 0, True, True)
        else:
            self.webhook_registered = self.myNetatmo.add_webhook()

        self.addNodes()
        self.wait_for_node_done()

        if not self.message_thread.is_alive():
            self.message_thread.start()

    def addNodes(self):
        logging.info('Adding selected weather stations')
        self.enabled_list = []
        self.homes_list = []
        primary_node_list = ['controller']  # controller is there for sure
        for home in self.home_ids:
            logging.debug('Adding from {}'.format(home))
            home_name = self.home_ids[home]['name']
            main_modules = self.myNetatmo.get_main_modules(home)
            logging.debug('main modules {} {} '.format(home, main_modules))
            for m_module in main_modules:
                logging.debug('{} Evalating MAIN module {} - {}'.format(home_name, m_module, main_modules))
                mod_name = main_modules[m_module]['name']
                node_name = home_name + '_' + mod_name
                node_address = self.getValidAddress(m_module)
                node_name = self.getValidName(node_name)
                tmp_module = {}
                tmp_module['home'] = home
                tmp_module['main_module'] = m_module
                logging.debug('Module {} enabled = {}'.format(node_name, self.myNetatmo.main_module_enabled(node_name)))
                if self.myNetatmo.main_module_enabled(node_name):
                    if tmp_module['home'] not in self.homes_list:
                        self.homes_list.append(tmp_module['home'])
                        self.myNetatmo.update_weather_info_cloud(home)
                        self.myNetatmo.update_weather_info_instant(home)

                    logging.debug('Names: {}, Addresses {} info {}'.format(node_name, node_address, tmp_module))
                    udiNetatmoWeatherMain(self.poly, node_address, node_address, node_name, self.myNetatmo, tmp_module)
                    primary_node_list.append(node_address)
                    time.sleep(1)
        # removing unused nodes
        while not self.configDone:
            logging.info('Waiting for config to comlete')
            time.sleep(1)
        logging.debug('Checking for nodes not used - node list {} - {} {}'.format(primary_node_list, len(self.nodes_in_db), self.nodes_in_db))
        for nde in range(0, len(self.nodes_in_db)):
            node = self.nodes_in_db[nde]

            logging.debug('Scanning db for extra nodes : {}'.format(node))
            if node['primaryNode'] not in primary_node_list:
                logging.debug('Removing node : {} {}'.format(node['name'], node))
                self.poly.delNode(node['address'])

        self.nodeDefineDone = True

    def configDoneHandler(self):
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()
        logging.info('configDoneHandler called')
        self.nodes_in_db = self.poly.getNodesFromDb()
        logging.debug('Nodes in Nodeserver - before cleanup: {} - {}'.format(len(self.nodes_in_db), self.nodes_in_db))
        self.configDone = True

    def systemPoll(self, polltype):
        if self.nodeDefineDone:
            logging.info('System Poll executing: {}'.format(polltype))
            nodes = self.poly.nodes()
            try:
                if 'longPoll' in polltype:
                    # Keep token current and refresh cloud daily min/max/trend values
                    self.myNetatmo.authendicated()
                    if not self.webhook_registered and self.webhookSuccess == 'Success':
                        self.webhook_registered = self.myNetatmo.add_webhook()
                        if self.webhook_registered:
                            self.node.setDriver('GV29', 1, True, True)
                    for home in self.homes_list:
                        self.myNetatmo.update_weather_info_cloud(home)
                        if not self.webhook_registered:
                            self.myNetatmo.update_weather_info_instant(home)

                    for nde in nodes:
                        if nde.address != 'controller':  # but not the setup node
                            logging.debug('updating node {} data'.format(nde))
                            nde.updateISYdrivers()

                if 'shortPoll' in polltype:
                    self.heartbeat()
                    # Real-time updates arrive via Netatmo webhooks; only poll /homestatus as fallback if webhook is not active
                    if not self.webhook_registered:
                        for home in self.homes_list:
                            self.myNetatmo.update_weather_info_instant(home)
                    for nde in nodes:
                        if nde.address != 'controller':  # but not the setup node
                            logging.debug('updating node {} data'.format(nde))
                            nde.updateISYdrivers()
            except Exception as e:
                logging.error('Exeption occcured : {}'.format(e))
        else:
            logging.info('System Poll - Waiting for all nodes to be added')

    def stopHandler(self):
        logging.info('Stop handler called')
        self.stop_processing_messages = True
        try:
            if self.webhook_registered:
                self.myNetatmo.drop_webhook()
        except Exception as e:
            logging.error(f'Error dropping webhook on stop: {e}')
        self.node.setDriver('GV29', 0, True, True)
        # Set nodes offline
        for node in self.poly.nodes():
            if hasattr(node, 'setOffline'):
                node.setOffline()
        self.poly.stop()

    def update(self, command=None):
        if self.nodeDefineDone:
            logging.info('update executing')
            nodes = self.poly.nodes()
            try:
                for home in self.homes_list:
                    self.myNetatmo.update_weather_info_cloud(home)
                    self.myNetatmo.update_weather_info_instant(home)
                for nde in nodes:
                    if nde.address != 'controller':  # but not the setup node
                        logging.debug('updating node {} data'.format(nde))
                        nde.updateISYdrivers()
            except Exception as e:
                logging.error('Exeption occcured : {}'.format(e))

    id = 'controller'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 2},
        {'driver': 'GV29', 'value': 99, 'uom': 25},
        {'driver': 'GV30', 'value': 99, 'uom': 25},
    ]
    commands = {
        'UPDATE': update,
        'TESTCON': webhook_test,
    }


if __name__ == "__main__":
    try:
        logging.info('starting')
        logging.info('Starting Netatmo Controller')
        polyglot = udi_interface.Interface([], {"enableWebhook": True})

        polyglot.start({'version': version, 'requestId': True})

        # Show the help in PG3 UI under the node's Configuration option
        polyglot.setCustomParamsDoc()

        # then you need to create the controller node
        NetatmoController(polyglot, 'controller', 'controller', 'Netatmo Weather')

        # We can start receive events
        polyglot.ready()

        # Just sit and wait for events
        polyglot.runForever()

    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)

    except Exception:
        logging.error(f"Error starting Nodeserver: {traceback.format_exc()}")
        polyglot.stop()




