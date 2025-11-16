from helpers.singleton import SingletonMeta
from typing import Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
from loguru import logger as log
import zipfile
#from serial.tools import list_ports




class GeneratorModel(str, Enum):
    #SMM100A = 'SMM100A' 
    SMBV100A = 'SMBV100A' 

DEFAULT_GENERATOR_IP =  "192.168.8.30"
DEFAULT_GENERATOR_PORT = 5025
DEFAULT_GENERATOR_MODEL = GeneratorModel.SMBV100A


class GeneratorSettings(BaseModel):
    frequency: float = 5e9
    transmit_power: float = -20.0
    transmission_enabled: bool = True
    
class GeneratorConnection(BaseModel):
    model: GeneratorModel = DEFAULT_GENERATOR_MODEL
    ip: str = DEFAULT_GENERATOR_IP
    port: int = DEFAULT_GENERATOR_PORT
    mode: str = "wlan"
    connection_type: str = "SOCKET"

class GeneratorConfig(BaseModel):
    settings: GeneratorSettings = GeneratorSettings()
    connection: GeneratorConnection = GeneratorConnection()
    
    @property
    def address(self) -> str:
        return f"{self.connection.ip}:{self.connection.port}"
    
    @property
    def model(self) -> GeneratorModel:
        return self.connection.model

# class GeneratorConnection(BaseModel):
#     mode: str = "wlan"  # "dvbt"
#     generator_model: GeneratorModel = DEFAULT_GENERATOR_MODEL
#     ip_address: str = ""
#     transmit_power: float = -20.0
#     transmission_enabled: bool =  True
#     frequency: float = 5e9
#     port: int = 5025
#     connection_type: str = "SOCKET"

#     model_config = {
#         "arbitrary_types_allowed" : True
#     }


# class GeneratorParams(BaseModel):
#     model: GeneratorModel
#     connection: Optional[GeneratorConnection] = None

#     def __init__(self, **data):
#         super().__init__(**data)
#         if not self.connection:
#             ip_map = {
#                 DEFAULT_GENERATOR_MODEL: "192.168.8.30",
#                 #GeneratorModel.SMBV100A: "192.168.8.30"
#                 #GeneratorModel.SMM100A: "192.168.8.160"

#             }
#             self.connection = GeneratorConnection(
#                 generator_model=self.model,
#                 ip_address=ip_map.get(self.model, "192.168.8.30")
#             )
#     model_config = {
#         "arbitrary_types_allowed" : True
#     }




class RxParams(BaseModel):
    samp_rate: float = 500e3 # 8e6
    rx_gain: float = 40.0
    count: int = 1
    buffer_size: int = int(40e3) #32768 #int(1e6) #1024
    N: int = 1


class UsrpParams(BaseModel):
    serial_map: Dict[str, str] = Field(default={
            '0' : '3273ADC',
            #'1' : '3273ACF',
        })
    agrs_template: str = "serial={serial}"

    def args_for(self, component_id: str) -> Optional[str]:
        ser = self.serial_map.get(component_id)
        return self.agrs_template.format(serial=ser) if ser else None

class RisParams(BaseModel):
    pattern: str = None
    index: int = None

RIS_SERIAL_MAP = {
    "0":"/dev/ttyUSB0",
    "1":"/dev/ttyUSB1"
}


class Params(BaseModel):

    def get_usrp_args(self, component_id: str) -> str:
        args = self.usrp.args_for(component_id)
        if not args:
            raise KeyError(
                f"Brak numeru seryjnego USRP dla component_id = {component_id}"
                f"Dodaj go w parametrs.py -> UsrpParams.serial_map"
            )
        return args
    
    frequency: float = 5e9
    #generator: GeneratorParams = GeneratorParams(model = DEFAULT_GENERATOR_MODEL)
    generator: GeneratorConfig = GeneratorConfig()
    rxes: RxParams = RxParams()
    usrp: UsrpParams = UsrpParams()
    rises: Dict[str, RisParams] = Field(default={
        '0': RisParams(),
        # '1': RisParams()
        
        
        
    })





class Parameters(metaclass=SingletonMeta):

    def __init__(self):
        self.data = Params()
    #    self._ris_port_map = self._scan_usb_ports()
        #self._ris_available_ports =  self._scan_usb_ports()

    #     for ris_id in self.data.rises:
    #         try:
    #             port = self.get_ris_port(ris_id)
    #             log.info("RIS {} przypisany do portu: {}", ris_id, port)
    #         except RuntimeError as e:
    #             log.error("Błąd przypisania portu do RIS {}: {}", ris_id, e)

    def get(self):
         return self.data
    
    # def get_ris_port(self, component_id: str) -> str:
    #     if component_id not in self._ris_port_map:
    #         raise RuntimeError(
    #             f'Bral portu USB dla RIS {component_id}.'
    #             f"Sprawdz numer seryjny w RIS_SERIAL_MAP."
    #         )
    #     return self._ris_port_map[component_id]
    
    # def _scan_usb_ports(self):
    #     ports = list_ports.comports()
    #     result = {}
    #     for p in ports:
    #         if p.serial_number is None:
    #             continue
            
    #         for ris_id, excepted_serial in RIS_SERIAL_MAP.items():
    #             if p.serial_number == excepted_serial:
    #                 result[ris_id] = p.device
    #                 log.info(f"RIS {ris_id} wykryty na porcie {p.device} (serial = {p.serial_number})")
                    
    #     return result
    
    
    #======================================================
    # def get_ris_port(self, component_id: str) -> str:
    #     if component_id in self._ris_port_map:
    #         return self._ris_port_map[component_id]

    #     if not self._ris_available_ports:
    #         raise RuntimeError(f"Brak dostępnych portów dla RIS {component_id}")

    #     port = self._ris_available_ports.pop(0)
    #     self._ris_port_map[component_id] = port
    #     log.debug("Przypisano RIS {} do portu {}", component_id, port)
    #     return port

    # def _scan_usb_ports(self):
    #     dev_list = os.listdir('/dev')
    #     usb_ports = [f"/dev/{d}" for d in dev_list if re.match(r"ttyUSB[0-9]+", d)]
    #     usb_ports.sort()
    #     return usb_ports

    def save_experyment_result_csv(self, data: np.ndarray) -> None:
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rx_count = data.shape[0]

        for rx in range(rx_count):
            filename = os.path.join(results_dir, f"experiment_result_rx_{rx}_{timestamp}.csv")
            df = pd.DataFrame(data[rx, :], columns=["Result"])
            log.debug("Saved experiment results to {}", filename)

