from fedot.api.api_utils.presets import Fedot_preset_helper
from fedot.core.repository.tasks import TaskTypesEnum, Task
from fedot.core.repository.operation_types_repository import get_operations_for_task

preset_checker = Fedot_preset_helper()

def test_presets_classification():
    task = Task(TaskTypesEnum.classification)

    class_operations = get_operations_for_task(task, mode='all')

    operations_for_light_preset = preset_checker.filter_operations_by_preset(task=task,
                                                                             preset='light')
    operations_for_ultra_light_preset = preset_checker.filter_operations_by_preset(task=task,
                                                                                   preset='ultra_light')

    assert len(operations_for_ultra_light_preset) < len(operations_for_light_preset) < len(class_operations)
    assert {'dt', 'logit', 'knn'} <= set(operations_for_ultra_light_preset)


def test_presets_regression():
    task = Task(TaskTypesEnum.regression)

    regr_operations = get_operations_for_task(task, mode='all')

    operations_for_light_preset = preset_checker.filter_operations_by_preset(task=task,
                                                                             preset='light')
    operations_for_ultra_light_preset = preset_checker.filter_operations_by_preset(task=task,
                                                                                   preset='ultra_light')

    assert len(operations_for_ultra_light_preset) < len(operations_for_light_preset) == len(regr_operations)
    assert {'dtreg', 'lasso', 'ridge', 'linear'} <= set(operations_for_ultra_light_preset)
