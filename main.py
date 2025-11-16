import sys
from loguru import logger as log
from helpers.exceptions import RestartRequired
from algorithms.algorithm import ExampleAlgorithm
from algorithms.experiment import ExampleExperiment
from controllers.launcher import create_controller

SYSTEM_CONTROLLER_ADDRESS ='localhost' #'192.168.8.219'
PORT_PUB_SUB = 5558
PORT_PUSH_PULL = 5559
TEST_MODE = True

EXPERIMENT_POWER_SETUP = [-30, -25, -20, None, -15] 
EXPERIMENT_RESULTS_DIR = "results" 

ALGO_SIGNAL_POWER = [10.0] 
ALGO_PATTERN_IDS  = [0] 
ALGO_RESULTS_DIR  = "results" 

        
algorithm = ExampleAlgorithm(
    signal_power=ALGO_SIGNAL_POWER, #[],
    pattern_ids=ALGO_PATTERN_IDS,
    results_dir=ALGO_RESULTS_DIR
)

experiment = ExampleExperiment(
    power_setup=EXPERIMENT_POWER_SETUP,
    results_dir=EXPERIMENT_RESULTS_DIR
)

log.remove()
log.add(sys.stderr, level="DEBUG") 


if __name__ == '__main__':
    
    if len(sys.argv) == 1:
        log.info('Starting SystemController')
        
        controller = create_controller(
            controller_type = "system",
            controller_id=0,
            port_pub= PORT_PUB_SUB,
            port_pull=PORT_PUSH_PULL,
            algorithm=algorithm,
            experiment=experiment,
            system_address=SYSTEM_CONTROLLER_ADDRESS,
            test_mode = TEST_MODE
        )
        
        try:
            controller.run()
        except KeyboardInterrupt:
            controller._broadcast_action("done")
            
    elif 2 <= len(sys.argv) <= 3:
        controller_type = sys.argv[1].strip().lower()
        controller_id = int(sys.argv[2]) if len(sys.argv) == 3 else 0
        
        while True:
            try:
                controller = create_controller(
                    controller_type=controller_type,
                    controller_id=controller_id,
                    port_pub=PORT_PUB_SUB,
                    port_pull=PORT_PUSH_PULL,
                    algorithm=algorithm,
                    experiment=experiment,
                    system_address=SYSTEM_CONTROLLER_ADDRESS,
                    test_mode=TEST_MODE
                )
                
                controller.run()
            except RestartRequired:
                log.info("Restarting {} controller...", controller_type)
                import time
                time.sleep(3)
    else:
        log.error("Unknown starting command")
