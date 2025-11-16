import zmq
import numpy as np
import time
from typing import Dict, Callable
from loguru import logger as log

from helpers.zmq_connection import ZmqServer
from helpers.parameters import Parameters
from algorithms.system_logic import SystemLogic
from algorithms.algorithm import Algorithm
from algorithms.experiment import Experiment

class SystemController:
    def __init__(self,
                 port_pub: int,
                 port_pull: int,
                 algorithm: Algorithm,
                 experiment: Experiment
                 ):
        
        log.info('SystemController created')
        
        self._connection = ZmqServer(
            port_pub=port_pub,
            port_pull=port_pull
        )
        self._system_logic = SystemLogic(
            algorithm=algorithm,
            experiment=experiment
        )
        
        self._generator_id: str | None = None
        self._ris_ids: str[str] = set()
        self._rx_ids: str[str] = set()
        
        self._reinit_in_progress = False

    def run(self) -> None:
        log.info("Waiting for all required components to register before starting system...")
        
        required_generator = True
        required_ris_ids = list(Parameters().get().rises.keys())
        requires_rx_count = Parameters().get().rxes.count
        
        timeout_s = 10
        start_time = time.time()
        
        while True:
            self._connection.receive_messages(self._handle_message_received)
            all_ok = True


            if required_generator and not self._generator_id:
                all_ok = False
                
            if len(self._ris_ids) < len(required_ris_ids):
                all_ok = False
                
            if len(self._rx_ids) < requires_rx_count:
                all_ok = False
            
            if all_ok:
                log.success("All component registered. Starting main")
                break
            
            if time.time() - start_time > timeout_s:
                log.warning("Timeout: not all components registered within {} s. Sending REINIT to all...", timeout_s)
                self._broadcast_action("reinit")
                start_time = time.time()
                
        while not self._system_logic.finished():
            self._connection.receive_messages(self._handle_message_received)
            self._generate_messages()
        self._broadcast_action("done")

        
    def _generate_messages(self):
        if self._system_logic.generate_measurement_command():
            log.debug('Start measurements')
            self._send_message({'component': 'rx', 'action': 'measure', 'data': {}})

        generator_request, rises_requests = self._system_logic.generate_configuration_change_requests()

        if generator_request is not None:
            if generator_request == Parameters().get().generator:
                log.debug('skip - generator configuration the same')
                self._system_logic.generator.received_ready('0')
            else:
                Parameters().get().generator = generator_request 
                self._send_message({
                    'component':'generator', 
                    'action': 'configure', 
                    'data': {
                    
                        'frequency': Parameters().get().frequency,
                        'transmit_power': Parameters().get().generator.connection.transmit_power,
                        'transmission_enabled': Parameters().get().generator.connection.transmission_enabled
                    
                    }})

        if rises_requests is not None:
            for ris_id, ris_request in rises_requests.items():
                if ris_request == Parameters().get().rises[ris_id]:
                    log.debug('skip - RIS {} configuration the same', ris_id)
                    self._system_logic.rises.received_ready(ris_id)
                else:
                    Parameters().get().rises[ris_id] = ris_request
                    log.debug('set RIS {} pattern {}', ris_id, ris_request.pattern)
                    self._send_message({
                        'component': 'ris', 
                        'id': ris_id, 
                        'action': 'configure', 
                        'data': ris_request.model_dump()
                        })

    def _send_message(self, message: Dict):
        self._connection.send_message(message)

    def _handle_message_received(self, message: Dict):
        log.debug('Received {}', message)
        if message['component'] == 'generator':
            self._handle_generator_message_received(message)
        elif message['component'] == 'ris':
            self._handle_ris_message_received(message)
        elif message['component'] == 'rx':
            self._handle_rx_message_received(message)
        else:
            log.warning('no handler defined for this component!')

    def _handle_generator_message_received(self, message: Dict):

        if 'id' in message and message['id'] is not None:
            self._generator_id = str(message['id'])

        match message['action']:
            case 'new':
                uid = message.get('_id')
                message['action'] = 'new-ack'
                message['data'] = self._system_logic.generator.received_new(device_id=message['id'], unique_id=uid)
                self._send_message(message)
            case 'ready':
                self._system_logic.generator.received_ready(device_id=message['id'])
                log.info('Generator is ready to operate.')
            case 'configure-ack':
                self._system_logic.generator.received_ready(device_id=message['id'])
                log.debug('Generator changed configuration.')
            case _:
                log.warning('Unknown generator action!')
 
    def _handle_ris_message_received(self, message: Dict): 
        if 'id' in message and message['id'] is not None:
            self._ris_ids.add(str(message['id'])) 
            
        match message['action']:
            case 'new':
                uid = message.get('_id')
                message['action'] = 'new-ack'
                message['data'] = self._system_logic.rises.received_new(device_id=message['id'], unique_id=uid)
                self._send_message(message)
            case 'ready':
                self._system_logic.rises.received_ready(device_id=message['id'])
                log.info('RIS {} is ready to operate.', message['id'])
            case 'configure-ack':
                self._system_logic.rises.received_ready(device_id=message['id'])
                log.debug('RIS {} changed configuration.', message['id'])
            case _:
                log.warning('Unknown RIS action!')
                

    def _handle_rx_message_received(self, message: Dict):
        
        if 'id' in message and message['id'] is not None:
            self._rx_ids.add(str(message['id']))


        match message['action']:
            case 'new':
                uid = message.get('_id')
                message['action'] = 'new-ack'
                message['data'] = self._system_logic.rxes.received_new(device_id=message['id'], unique_id=uid)
                self._send_message(message)
            case 'ready':
                self._system_logic.rxes.received_ready(device_id=message['id'])
                log.info('RX {} is ready to operate.', message['id'])
            case 'measure-ack':
                self._system_logic.rxes.received_ready(device_id=message['id'])
                self._system_logic.receive_measurement_results(device_id=message['id'], results=message['data'])

                log.debug('RX {} measured: {}', message['id'], message['data'])
            case "component-reinit":
                
                if self._reinit_in_progress:
                    log.warning("Ignoring RX reinit request (already in progress)")
                    return

                log.debug("RX {} requests reinit", message['id'])
                
                self._reinit_in_progress = True
                
                self._broadcast_action("reinit")
                
                if message.get('need_config'):
                    cfg = self._system_logic.rxes.received_new(
                        device_id=message['id'],
                        unique_id=message.get('_id') 
                    )
                    
                    log.warning('Sending fresh RX config after reinit')
                    self._send_message({
                        'component' : 'rx',
                        'id' : message['id'],
                        'action' : 'configure',
                        'data' : cfg
                    })
                
                self._reinit_in_progress = False
                
                
            case _:
                log.warning('Unknown RX action')
    
    def _broadcast_action(self, action: str) -> None:
        log.warning("Broadcast '{}' to all known components", action)
        
        gen_id = self._generator_id or "0"
        self._send_message({
            'component' : 'generator',
            'id' : gen_id,
            'action' : action
        })
        
        ris_id = sorted(self._ris_ids) if self._ris_ids else list(Parameters().get().rises.keys())
        for rid in ris_id:
            self._send_message({
                'component' : 'ris',
                'id' : str(rid),
                'action' : action
            })
        
        rx_count = Parameters().get().rxes.count
        for i in range(rx_count):
            self._send_message({
                'component': 'rx',
                'id': str(i),
                'action': action
            })
            

