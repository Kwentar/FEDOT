from abc import abstractmethod

import numpy as np
from sklearn.metrics import f1_score, mean_squared_error, roc_auc_score

from core.chain_validation import validate
from core.composer.chain import Chain
from core.models.data import InputData


def from_maximised_metric(metric_func):
    def wrapper(*args, **kwargs):
        return -metric_func(*args, **kwargs)

    return wrapper


class ChainMetric:
    @staticmethod
    @abstractmethod
    def get_value(chain: Chain, reference_data: InputData) -> float:
        raise NotImplementedError()


class RmseMetric(ChainMetric):
    @staticmethod
    def get_value(chain: Chain, reference_data: InputData) -> float:
        results = chain.predict(reference_data)
        return mean_squared_error(y_true=reference_data.target, y_pred=results.predict)


class F1Metric(ChainMetric):
    @staticmethod
    @from_maximised_metric
    def get_value(chain: Chain, reference_data: InputData) -> float:
        results = chain.predict(reference_data)
        bound = np.mean(results.predict)
        predicted_labels = [1 if x >= bound else 0 for x in results.predict]
        return f1_score(y_true=reference_data.target, y_pred=predicted_labels)


class MaeMetric(ChainMetric):
    @staticmethod
    def get_value(chain: Chain, reference_data: InputData) -> float:
        results = chain.predict(reference_data)
        return mean_squared_error(y_true=reference_data.target, y_pred=results.predict)


class RocAucMetric(ChainMetric):
    @staticmethod
    @from_maximised_metric
    def get_value(chain: Chain, reference_data: InputData) -> float:
        n_classes = reference_data.num_classes
        if n_classes > 2:
            additional_params = {'multi_class': 'ovo', 'average': 'macro'}
        else:
            additional_params = {}

        try:
            validate(chain)
            results = chain.predict(reference_data)
            try:
                score = round(roc_auc_score(y_score=results.predict,
                                            y_true=reference_data.target,
                                            **additional_params), 3)
            except ValueError as ex:
                print(f'ROC AUC can not be calculated: {ex}')
                score = 0.5
        except Exception as ex:
            print(f'Metric evaluation error: {ex}')
            score = 0.5
        return score


# TODO: reference_data = None ?
class StructuralComplexityMetric(ChainMetric):
    @staticmethod
    def get_value(chain: Chain, reference_data: InputData) -> float:
        return chain.depth ** 2 + chain.length


class NodeNum(ChainMetric):
    @staticmethod
    def get_value(chain: Chain, reference_data: InputData) -> float:
        return chain.length
