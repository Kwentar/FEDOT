from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional


@dataclass
class TaskParams:
    pass


@dataclass
class TsForecastingParams(TaskParams):
    forecast_length: int
    max_window_size: int
    period: int


class TaskTypesEnum(Enum):
    classification = 'classification',
    regression = 'regression',
    ts_forecasting = 'ts_forecasting'
    clustering = 'clustering'  # not applicable as main task yet


@dataclass
class Task:
    task_type: TaskTypesEnum
    task_params: Optional[TaskParams] = None


# local tasks that can be solved as a part of global tasks
def compatible_task_types(main_task_type: TaskTypesEnum) -> List[TaskTypesEnum]:
    _compatible_task_types = {
        TaskTypesEnum.ts_forecasting: [TaskTypesEnum.regression],
        TaskTypesEnum.classification: [TaskTypesEnum.clustering],
        TaskTypesEnum.regression: [TaskTypesEnum.clustering]
    }
    if main_task_type not in _compatible_task_types:
        return []
    return _compatible_task_types[main_task_type]


def extract_task_param(task: Task) -> Any:
    try:
        task_params = task.task_params
        if isinstance(task_params, TsForecastingParams):
            window_len = task_params.max_window_size
            prediction_len = task_params.forecast_length
            return window_len, prediction_len
        else:
            raise ValueError('Incorrect parameters type for data')
    except AttributeError as ex:
        raise AttributeError(f'Params are required for the {task} task: {ex}')
