import zmq
from loguru import logger as log
import time
#import json

from typing import Dict, Callable
from helpers.zmq_connection import ZmqClient
from controllers.controller import Controller
from helpers.parameters import GeneratorConfig, Parameters, GeneratorModel


class GeneratorController(Controller):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._generator = None
        
        params = Parameters().get().generator 
        
        self._model = params.model
        self._ip_address = params.connection.ip
        self._port = params.connection.port
        #self._mode = params.connection.mode
        self._connection_type  = params.connection.connection_type
        
        self._frequency = params.settings.frequency
        self._transmit_power = params.settings.transmit_power
        self._transmission_enabled = params.settings.transmission_enabled
        


        if not self._test_mode:
            try:
                resource = f'TCPIP::{self._ip_address}::{self._port}::{self._connection_type}'
                if self._model == GeneratorModel.SMM100A:
                     from RsSmw import RsSmw
                     self._generator = RsSmw(resource, True, False, "SelectVisa='socket'")
                if self._model == GeneratorModel.SMBV100A:
                    from RsSmbv import RsSmbv 
                    self._generator = RsSmbv(resource, True, False, "SelectVisa='socket'")
                
                log.info(f"[INFO] Connected to generator {self._model} at {resource}")
            except Exception as e:
                log.error(f"[ERROR] Error connecting to generator: {e}")
                exit()

    def _perform_reinit(self) -> None:
        try:
            if not self._test_mode:
                self._generator.output.state.set_value(False)
                log.info("[GENERATOR] RF off")
        except Exception as e:
            log.error(f"[GENERATOR] RF disable faild during reinit because: {e}")
        try:
            self._transmission_enabled = False
        except Exception:
            pass


    def _on_message_received(self, message: Dict):
        match message['action']:
            case 'new-ack':
                config = message['data']
                self._configure_generator(config)
                self._send_message({'action': 'ready'})
            case 'configure':
                config = message['data']
                self._configure_generator(config)
                self._send_message({'action': 'configure-ack'})
            case 'noise':
                self._configure_noise()
                self._send_message({'action': 'noise-ack'})
            case 'reinit':
                log.warning("[GENERATOR] REINIT requested")
                self._perform_reinit()
                self._send_message({'action' : 'new'})
            case 'done':
                log.warning("[GENERATOR] Finish")

            case _:
                log.warning('this action is not defined!')

    def _configure_generator(self, config: Dict):
        print(config)
        if self._test_mode:
            log.info('(TEST) generator configured')
            return

        if 'frequency' in config:
            self._frequency = config['frequency']

        if 'transmit_power' in config:
            self._transmit_power = config['transmit_power']

        if 'transmission_enabled' in config:
            self._transmission_enabled = config['transmission_enabled']
        
        if not self._test_mode and self._generator:
            if self._model == "SMM100A":
                self._generator.source.frequency.fixed.set_value(self._frequency)
                self._generator.source.power.level.immediate.set_amplitude(self._transmit_power)
                self._generator.output.state.set_value(self._transmission_enabled) 
            elif self._model == "SMBV100A":
                self._generator.source.frequency.fixed.set_value(self._frequency)
                self._generator.source.power.level.immediate.set_amplitude(self._transmit_power)
                self._generator.output.state.set_value(self._transmission_enabled)

                
            log.info(f"[GENERATOR] {self._model} Configured: Frequency = {self._frequency} Hz, Power = {self._transmit_power} dBm, Enabled = {self._transmission_enabled}")
    
    def _noise(self):
        if self._test_mode:
            log.info('(TEST) Generator set to noise mode')
            return
        if not self._test_mode and self._generator:
            self._generator.output.state.set_value(False)
            log.info("[GENERATOR] Set to noise mode")









