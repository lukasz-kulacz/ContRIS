import zmq
from loguru import logger as log
# import time
import json
# from RsSmw import *
import re
import subprocess

import numpy as np
from typing import Dict, Callable, List, Tuple
from helpers.zmq_connection import ZmqClient
from controllers.controller import Controller
import time
from helpers.parameters import Params

usrp = None 


class RxController(Controller):

    def _list_available_usrp_serials(self) -> Tuple[List[str], List[Dict]]:
        try:
            import uhd
            global usrp
            try:
                out = subprocess.check_output(["uhd_find_devices"], text=True)
                serials = re.findall(r"serial=(\w+)", out)

            except Exception as e:
                log.warning(f"Could not execute uhd_find_devices: {e}")
        except Exception:
            log.debug("UHD module not available.")
        
    def _init_usrp_from_params(self) -> bool:
        global usrp
        if self._test_mode:
            print(f"(TEST) USRP init ok")
            usrp = "TEST USRP"
            return True
        else:
            try:
                import uhd
                params = Params()
                usrp_args = params.get_usrp_args(self._component_id)
                usrp = uhd.usrp.MultiUSRP(usrp_args) 
                self._usrp_usb_sn = params.usrp.serial_map.get(self._component_id)
                log.info(f"USRP reinitialized successfully (ID: {self._component_id}).")
                return True
            except Exception as e:
                self._list_available_usrp_serials()
                log.error(f"USRP reinitialization failed: {e}")
                usrp = None
                return False
    
    def _notify_reinit(self, reason: str) -> None:
        payload = {
            'action' : 'component-reinit',
            'component' : 'rx',
            'id': self._component_id,
            'reason' : reason,
            'need_config' : True
            
        }

        self._send_message(payload)
        log.warning(f"[RX {self._component_id}] Sent reinit request (need_config=True). Reason: {reason}")
        
    def _reset_usrp_with_backoff(self, reason: str) -> bool:
        global usrp
        if self._test_mode:
            log.info("(TEST) Ignoring USRP reset (no hardware).")
            return True
        
        self._consecutive_failures += 1
        wait_s = min(2**(self._consecutive_failures - 1), 60)
        log.warning(f"[RX {self._component_id}] Resetting USRP due to: {reason}. Sleeping {wait_s}s...")
        try:
            del usrp
        except Exception:
            pass
        
        time.sleep(wait_s)
        ok = self._init_usrp_from_params()
        
        if ok:
            log.info(f"[RX {self._component_id}] USRP recovered after reset.")
            self._consecutive_failures = 0
            self._awaiting_reconfig = True
            self._notify_reinit(reason)
        return ok
        
    def _recv_samples_safe(self) -> np.ndarray:
        global usrp
        
        if self._test_mode:
            noise = (np.random.randn(self._buffer_size) + 1j*np.random.randn(self._buffer_size)) * 0.1
            return noise
        
        max_attempts = self._max_attempts_per_read
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            try:
                samples = usrp.recv_num_samps(
                    self._buffer_size,
                    self._frequency,
                    self._samp_rate,
                    [0],
                    self._rx_gain
                )

                self._consecutive_failures = 0
                return samples
            except Exception as e:
                msg = str(e)
                log.error(f"[RX {self._component_id}] recv_num_samps exception "
                          f"(attempt {attempt}/{max_attempts}): {msg}")

                transient = any(s in msg for s in[
                    "LIBUSB_TRANSFER_OVERFLOW",
                    "LIBUSB_TRANSFER_ERROR",
                    "LIBUSB_ERROR_NO_DEVICE",
                    "transfer overflow",
                    "accum_timeout",
                    "timeout",
                    "safe-call"
                ])

                if transient:
                    if not self._reset_usrp_with_backoff(msg):
                        continue
                else:
                    raise
        raise RuntimeError(f"[RX {self._component_id}] Failed to retrieve samples after multiple attempts.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._avg_power_history = -100.0 
        self._log_history_coeff = 0.95

        self._frequency = None
        self._samp_rate = None
        self._rx_gain = None
        self._buffer_size = None #327680
        self._N = None #8
        self._usrp_usb_sn = None

        self._max_attempts_per_read = 5 # liczba prob resetu
        self._consecutive_failures = 0 

        if self._test_mode:
            log.info(f"(TEST) Simulating USRP connection for RX {self._component_id}")
            self._init_usrp_from_params()
        else:
            #time.sleep(10)
            import uhd
            global usrp
            params = Params()
            try:
                usrp_args = params.get_usrp_args(self._component_id)
                try:
                    usrp = uhd.usrp.MultiUSRP(usrp_args)
                    log.info(f"[RX {self._component_id}] Connected to USRP.")
                except:
                    self._list_available_usrp_serials()
                    log.warning(f"No USRP entry found for RX ID '{self._component_id}'")

                
                self._usrp_usb_sn = params.usrp.serial_map.get(self._component_id)
            except Exception as e:
                log.error(f"[RX {self._component_id}] Failed to initialize USRP: {e}")
                usrp = None

    def _on_message_received(self, message: Dict):
        match message['action']:
            case 'new-ack':
                config = message['data']
                self._configure_rx(config)
                self._send_message({'action': 'ready'})
            case 'configure':
                config =  message['data']
                self._configure_rx(config)
                self._send_message({'action' : 'configure-ack'})
                self._send_message({'action' : 'ready'})
            case 'measure':
                config = message['data']
                result = self._measure(config)
                self._send_message({'action': 'measure-ack', 'data': result})
                # reason = "LIBUSB_TRANSFER_OVERFLOW"
                # self._notify_reinit(reason)
                # time.sleep(50)
            case 'reinit':
                log.warning('[RX {}] REINIT requested', self._component_id)

                if self._test_mode:
                    log.info("(TEST) Ignoring REINIT request.")
                    return

                ok = self._init_usrp_from_params()
                if ok:
                    log.success("[RX {}] USRP reinitialized successfully.", self._component_id)

            case 'done':
                log.warning("[RX] Finish")

            case _:
                log.warning('this action is not defined!')

    def _configure_rx(self, config: Dict):
        if self._test_mode:
            log.info('(TEST) RX {} configured', self._component_id)

        if 'frequency' in config:
            self._frequency = config['frequency']

        if 'samp_rate' in config:
            self._samp_rate = config['samp_rate']

        if 'rx_gain' in config:
            self._rx_gain = config['rx_gain']
            
        if 'buffer_size' in config:
            self._buffer_size = config['buffer_size']
            
        if 'N' in config: 
            self._N = config['N']
        
        if not self._test_mode:
            log.info(f"RX Configured: Frequency = {self._frequency} Hz, Gain = {self._rx_gain} dB, sample rate = {self._samp_rate} S/s")
 


    def _measure(self, config: Dict) -> List[float]:
        if self._test_mode:
            result = -80 + np.random.rand() * 20
            self._avg_power_history = pow(10.0, self._avg_power_history / 10.0) * self._log_history_coeff
            self._avg_power_history += pow(10.0, result / 10.0) * (1.0 - self._log_history_coeff)
            self._avg_power_history = 10.0 * np.log10(self._avg_power_history)
            log.info(f"Avg: {self._avg_power_history:.2f} dBm; Current: {result:.2f} dBm")
            return [result] 
            
        power_measurements = []
        while len(power_measurements) < self._N:
            samples = self._recv_samples_safe()
            power_lin = np.mean(np.abs(samples) ** 2)
            power_log = 10 * np.log10(power_lin)
            power_measurements.append(float(power_log))

            self._avg_power_history = pow(10.0, self._avg_power_history / 10.0) * self._log_history_coeff
            self._avg_power_history += power_lin * (1.0 - self._log_history_coeff)
            self._avg_power_history = 10.0 * np.log10(self._avg_power_history)
            log.info(f"Avg: {self._avg_power_history:.2f} dBm; Current: {power_log:.2f} dBm")
        return power_measurements
