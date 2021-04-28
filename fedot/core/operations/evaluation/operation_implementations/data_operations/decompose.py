import numpy as np

from typing import Optional

from fedot.core.operations.evaluation.operation_implementations.\
    implementation_interfaces import DataOperationImplementation


class DecomposerImplementation(DataOperationImplementation):
    """ Class for decomposing target """

    def __init__(self, **params: Optional[dict]):
        super().__init__()
        self.params = None

    def fit(self, input_data):
        """
        The decompose operation doesn't support fit method
        """
        pass

    def transform(self, input_data, is_fit_chain_stage: Optional[bool]):
        """
        Method for modifying input_data
        :param input_data: data with features, target and ids
        :param is_fit_chain_stage: is this fit or predict stage for chain
        :return input_data: data with transformed features attribute
        """

        features = np.array(input_data.features)
        # Array with masks
        masked_features = np.array(input_data.masked_features)

        # TODO Implement: first parent must be "Data parent"
        # Get prediction from "Model parent"
        prev_prediction_id = np.ravel(np.argwhere(masked_features == 0))
        prev_prediction = features[:, prev_prediction_id]

        # Get prediction from "Data parent"
        prev_features_id = np.ravel(np.argwhere(masked_features != 0))
        prev_features = features[:, prev_features_id]

        if is_fit_chain_stage:
            # Calculate difference between prediction of model and current target
            diff = input_data.target - prev_prediction
            # Update target
            input_data.target = diff
        else:
            # For predict stage don't perform any operations
            pass

        # Create OutputData
        output_data = self._convert_to_output(input_data, prev_features)
        # We decompose the target, so in the future we need to ignore
        output_data.target_action = 'ignore'
        return output_data

    def get_params(self):
        return None
