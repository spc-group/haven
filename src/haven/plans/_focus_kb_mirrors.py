import enum

# import numpy as np
import os
from pathlib import Path

from aps.ai.beamline_controller.execution.execution_manager import ExecutionManager
from aps.ai.beamline_controller.gui.beamline_controller import APPLICATION_NAME
from aps.common.initializer import IniMode, register_ini_instance
from aps.common.logger import (
    DEFAULT_STREAM,
    LoggerMode,
    register_logger_single_instance,
)
from aps.common.widgets.congruence import check_and_create_directory

# np.NaN = np.nan  # required for aps.ai, but fails mypy type-checking


ini_file_name = ".beamline-controller.json"
logger_mode = LoggerMode.FULL


class AITypes(enum.IntEnum):
    OPTIMIZATION = 0
    NEURAL_NETWORKS = 1


class Optimizer(enum.IntEnum):
    MOBO = 0
    SOBO = 1
    SONL = 2


# To-do:
# - Merge logging with Haven's logging system
# - Convert os.chdir to pathlib
# - Find a place to keep the working directory files
#     (/net/s25data/xorApps/bluesky/...)
# -


def focus_kb_mirrors(use_digital_twin: bool): ...


def _focus_kb_mirrors(base_directory: Path, optical_system_id: str):
    """Inner Bluesky plan for connecting to the automated focusing of a
    set of KB mirrors.

    """
    working_directory = base_directory / optical_system_id
    check_and_create_directory(None, str(working_directory), "Working Directory")
    os.chdir(working_directory)

    register_ini_instance(
        ini_mode=IniMode.LOCAL_JSON_FILE,
        ini_file_name=ini_file_name,
        application_name=APPLICATION_NAME,
    )
    register_logger_single_instance(
        stream=DEFAULT_STREAM,
        logger_mode=logger_mode,
        application_name=APPLICATION_NAME,
    )
    execution_manager = ExecutionManager(
        application_name=APPLICATION_NAME,
        beamline_id=optical_system_id,
        working_directory=working_directory,
        run_as_generator=True,
    )
    # Do the actual plan
    yield from execution_manager.start_ai_agent()
    # See how the optimization turned out...
    ai_result = execution_manager.get_current_result()
    initialization_parameters = (
        execution_manager.get_current_initialization_parameters()
    )  # initialization parameters used by the agent
    ai_type = initialization_parameters.get_parameter("ai_type")
    if ai_result is not None:
        if ai_type == AITypes.OPTIMIZATION:
            if (
                initialization_parameters.get_parameter("optimizer_type")
                == Optimizer.MOBO
            ):
                optimization_result_data, pareto_front_data, best_trial_data = ai_result
            else:
                optimization_result_data, best_trial_data = ai_result

            if (
                not optimization_result_data is None
                and not optimization_result_data.is_empty()
            ):
                if (
                    initialization_parameters.get_parameter("optimizer_type")
                    == Optimizer.MOBO
                ):
                    if (
                        not pareto_front_data is None
                        and not pareto_front_data.is_empty()
                    ):
                        print(
                            f" Pareto Frontier, Trial Numbers: {pareto_front_data.get_trial_numbers()}"
                        )
                    else:
                        raise Exception(
                            "Inconclusive Optimization: Pareto Front is Empty"
                        )

                selected_trial = best_trial_data.trial_number
            else:
                raise Exception(
                    "Inconclusive Optimization: Optimization Result is Empty"
                )
        elif ai_type == AITypes.NEURAL_NETWORKS:
            selected_trial = 1

        trial_data, beam_properties = execution_manager.get_trial(
            selected_trial, initialization_parameters
        )

        print("\nSelected Best Trial #:", trial_data.trial_number)
        print("\n\nMOVE MOTORS TO TRIAL DATA")

        yield from execution_manager.move_motors_to_trial_data(trial_data)
        return ai_result
