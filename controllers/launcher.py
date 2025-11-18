from controllers.system_controller import SystemController
from controllers.generator_controller import GeneratorController
from controllers.rx_controller import RxController
from controllers.ris_controller import RisController
from helpers.parameters import Parameters


def create_controller(
    controller_type: str, 
    controller_id: int,
    algorithm=None,
    experiment=None
    ):
   

    match controller_type:
        case 'system':
            return SystemController(
                port_pub = Parameters().system_controller_port_pub_sub,
                port_pull = Parameters().system_controller_port_push_pull,
                algorithm = algorithm,
                experiment = experiment
            )
        case 'generator':
            return GeneratorController(
                component_name = controller_type,
                component_id = str(controller_id),
                controller_address = Parameters().system_controller_ip_address,
                port_sub = Parameters().system_controller_port_pub_sub,
                port_push = Parameters().system_controller_port_push_pull,
                test_mode = Parameters().test_mode
            )
        case 'rx':
            return RxController(
                component_name = controller_type,
                component_id = str(controller_id),
                controller_address = Parameters().system_controller_ip_address,
                port_sub = Parameters().system_controller_port_pub_sub,
                port_push = Parameters().system_controller_port_push_pull,
                test_mode = Parameters().test_mode
            )
        
        case 'ris':
            return RisController(
                component_name = controller_type,
                component_id = str(controller_id),
                controller_address = Parameters().system_controller_ip_address,
                port_sub = Parameters().system_controller_port_pub_sub,
                port_push = Parameters().system_controller_port_push_pull,
                test_mode = Parameters().test_mode
            )
        case _:
            raise ValueError(f"Unknown controller type '{controller_type}'")