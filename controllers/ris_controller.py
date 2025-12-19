import time
from typing import Dict

from serial import Serial
from loguru import logger as log

from controllers.controller import Controller
from helpers.parameters import RisConfigChangeRequest


class RisController(Controller):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ser = None

        port = self._parameters.ris_serial_map[self._component_id]
        log.info(f"[RIS {self._component_id}] uses serial port {port}")

        if not self._test_mode:
            try:
                self.ser = Serial(port, baudrate=self._parameters.ris_serial_boudrate, timeout=self._parameters.ris_serial_timeout)
                self.ser.flushInput()
                self.ser.flushOutput()
                log.info(f"[RIS {self._component_id}] Serial connection established.")
            except Exception as e:
                raise RuntimeError(f"Failed to open serial port {port}: {e}")

    def _on_message_received(self, message: Dict):
        match message['action']:
            case 'new-ack':
                self._send_message({'action': 'ready'})
                
            case 'configure':
                config = message['data']
                config = RisConfigChangeRequest(**config)
                self._configure_ris(config)
                self._send_message({'action': 'configure-ack'})
            case _:
                log.warning(f"[RIS {self._component_id}] Unknown action received.")

    def _configure_ris(self, config: RisConfigChangeRequest):
        log.info(f"SET {config.pattern_index}: {config.pattern_hex}")
        if self._test_mode:
            return

        self._pattern = config.pattern_hex
        self._set_pattern(self._pattern.encode("utf-8"))
            
    def _set_pattern(self, pattern: str) -> bool:
        if not pattern:
            log.error("Invalid pattern received")
            return False
        
        self.ser.flushInput()
        self.ser.flushOutput()
        self.ser.write(b"!" + pattern + b"\n")
        start_time = time.time()
        while True:
            response = self.ser.readline()
            if response.strip() == b"#OK":
                return True
            if time.time() - start_time > self._parameters.ris_serial_timeout:
                log.error("RIS: Timeout during pattern setting.")
                return False

        