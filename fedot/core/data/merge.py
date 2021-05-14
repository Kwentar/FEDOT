import numpy as np
from typing import List
from fedot.core.repository.dataset_types import DataTypesEnum


class DataMerger:
    """
    Class for merging data, when it comes from different nodes and there is a
    need to merge it into next level node

    :param outputs: list with OutputData from parent nodes
    """

    def __init__(self, outputs: list):
        self.outputs = outputs

    def merge(self):
        """ Method automatically determine which merge function should be
        applied """
        merge_function_by_type = {DataTypesEnum.ts: self.combine_datasets_ts,
                                  DataTypesEnum.table: self.combine_datasets_table,
                                  DataTypesEnum.text: self.combine_datasets_table}

        first_data_type = self.outputs[0].data_type
        output_data_types = []
        for output in self.outputs:
            output_data_types.append(output.data_type)

        # Check is all data types can be merged or not
        if len(set(output_data_types)) > 1:
            raise ValueError("There is no ability to merge different data types")

        # Prepare mask with predict from different parent nodes
        if first_data_type == DataTypesEnum.table and len(self.outputs) > 1:
            masked_features = self.prepare_parent_mask(self.outputs)
        else:
            masked_features = None

        # Define appropriate strategy
        merge_func = merge_function_by_type.get(first_data_type)
        if merge_func is None:
            message = f"For data type '{first_data_type}' doesn't exist merge function"
            raise NotImplementedError(message)
        else:
            idx, features, target, target_action, task = merge_func()

        return idx, features, target, masked_features, target_action, task, first_data_type

    def combine_datasets_table(self):
        """ Function for combining datasets from parents to make features to
        another node. Features are tabular data.

        :return idx: updated indices
        :return features: new features obtained from predictions at previous level
        :return target: updated target
        """
        are_lengths_equal, idx_list = self._check_size_equality(self.outputs)

        if are_lengths_equal:
            idx, features, target, target_action, task = self._merge_equal_outputs(self.outputs)
        else:
            idx, features, target, target_action, task = self._merge_non_equal_outputs(self.outputs,
                                                                                       idx_list)

        return idx, features, target, target_action, task

    def combine_datasets_ts(self):
        """ Function for combining datasets from parents to make features to
        another node. Features are time series data.

        :return idx: updated indices
        :return features: new features obtained from predictions at previous level
        :return target: updated target
        """
        are_lengths_equal, idx_list = self._check_size_equality(self.outputs)

        if are_lengths_equal:
            idx, features, target, target_action, task = self._merge_equal_outputs(self.outputs)
        else:
            idx, features, target, target_action, task = self._merge_non_equal_outputs(self.outputs,
                                                                                       idx_list)

        features = np.ravel(np.array(features))
        target = np.ravel(np.array(target))
        return idx, features, target, target_action, task

    @staticmethod
    def prepare_parent_mask(outputs):
        """ The method for outputs from multiple parent nodes prepares a field
        with encoded values

        :param outputs: list with OutputData
        :return masked_features: list with masked features
        """

        # For each parent output prepare mask
        current_flag = 0
        masked_features = []
        for output in outputs:
            predicted_values = np.array(output.predict)
            # Calculate columns
            table_shape = predicted_values.shape

            # Calculate columns
            if len(table_shape) == 1:
                features_amount = 1
            else:
                features_amount = table_shape[1]

            mask = [current_flag]*features_amount
            masked_features.extend(mask)

            # Update flag
            current_flag += 1

        return masked_features

    @staticmethod
    def _merge_equal_outputs(outputs: list):
        """ Method merge datasets with equal amount of rows """

        features = []
        for elem in outputs:
            if len(elem.predict.shape) == 1:
                features.append(elem.predict)
            else:
                # If the model prediction is multivariate
                number_of_variables_in_prediction = elem.predict.shape[1]
                for i in range(number_of_variables_in_prediction):
                    features.append(elem.predict[:, i])

        features = np.array(features).T
        idx = outputs[0].idx
        # If the amount of parent nodes is equal to 1
        if len(outputs) == 1:
            target = outputs[0].target
            target_action = outputs[0].target_action
            task = outputs[0].task
        else:
            # Update target from multiple parents
            target, target_action, task = TaskTargetMerger(outputs).obtain_equal_target()

        return idx, features, target, target_action, task

    @staticmethod
    def _merge_non_equal_outputs(outputs: list, idx_list: List):
        """ Method merge datasets with different amount of rows by idx field """

        # Search overlapping indices in data
        for i, idx in enumerate(idx_list):
            idx = set(idx)
            if i == 0:
                common_idx = idx
            else:
                common_idx = common_idx & idx

        # Convert to list
        common_idx = np.array(list(common_idx))
        if len(common_idx) == 0:
            raise ValueError(f'There are no common indices for outputs')

        idx_list = [list(output.idx) for output in outputs]
        predicts = [output.predict for output in outputs]

        # Generate feature table with overlapping ids
        features = tables_mapping(idx_list, predicts, common_idx)
        # Link tables with features into one table
        features = np.array(features).T

        # Merge tasks and targets
        t_merger = TaskTargetMerger(outputs)
        filtered_target, target_action, task = t_merger.obtain_non_equal_target(common_idx)
        return common_idx, features, filtered_target, target_action, task

    @staticmethod
    def _check_size_equality(outputs: list):
        """ Function check the size of combining datasets """
        idx_lengths = []
        idx_list = []
        for elem in outputs:
            idx_lengths.append(len(elem.idx))
            idx_list.append(elem.idx)

        # Check amount of unique lengths of datasets
        if len(set(idx_lengths)) == 1:
            are_lengths_equal = True
        else:
            are_lengths_equal = False

        return are_lengths_equal, idx_list


class TaskTargetMerger:
    """ Class for merging target and tasks """

    def __init__(self, outputs):
        self.outputs = outputs

    def obtain_equal_target(self):
        """ Method can merge different targets if the amount of objects in the
        training sample are equal
        """

        # Get actions for target and tasks
        actions, targets, tasks = self._disintegrate_outputs()

        # If all actions is empty - there is no need to merge targets
        if all(action is None for action in actions):
            target = self.outputs[0].target
            task = self.outputs[0].task
            target_action = None
            return target, target_action, task
        # If there is an "ignore" action - need to apply intelligent merge
        elif any(action == 'ignore' for action in actions):
            target, target_action, task = self.ignored_merge(targets, actions, tasks)
            return target, target_action, task

    def obtain_non_equal_target(self, common_idx):
        """ Method for merging targets which have different amount of objects
        (amount of rows)

        :param common_idx: array with indices of common objects
        """

        # Get actions for target and tasks
        actions, targets, tasks = self._disintegrate_outputs()

        # Match targets - make them equal
        idx_list = [output.idx for output in self.outputs]
        mapped_targets = tables_mapping(idx_list, targets, common_idx)

        # If all actions is empty - there is no need to merge targets
        if all(action is None for action in actions):
            # Just applying merge operation for common_idx
            filtered_target = mapped_targets[0]

            task = tasks[0]
            target_action = None
            return filtered_target, target_action, task
        elif any(action == 'ignore' for action in actions):
            new_mapped_targets = []
            # Convert targets into tables:
            for target in mapped_targets:
                if len(target.shape) == 1:
                    new_mapped_targets.append(target.reshape((-1, 1)))
            new_mapped_targets = np.array(new_mapped_targets)
            filtered_target, target_action, task = self.ignored_merge(new_mapped_targets,
                                                                      actions,
                                                                      tasks)
            return filtered_target, target_action, task

    def _disintegrate_outputs(self):
        """
        Method extract actions, targets and tasks from list with OutputData
        """
        actions = [output.target_action for output in self.outputs]
        targets = [output.target for output in self.outputs]
        tasks = [output.task for output in self.outputs]

        return actions, targets, tasks

    @staticmethod
    def ignored_merge(targets, actions, tasks):
        """ Method merge targets with 'ignore' labels """
        main_ids = np.ravel(np.argwhere(np.array(actions) != 'ignore'))
        targets = np.array(targets)
        tasks = np.array(tasks)

        # Is there is chain predict stage without target at all
        if targets[0] is None:
            target = None
            target_action = None
        # If there are several known targets
        else:
            target = targets[main_ids]
            target = target[0, :, :]
            target_action = None

        task = tasks[main_ids]
        task = task[0]
        return target, target_action, task


def tables_mapping(idx_list, object_list, common_idx):
    """ The function maps tables by matching object indices

    :param idx_list: list with indices for mapping
    :param object_list: list with tables (with features, targets or predictions)
     for mapping
    :param common_idx: list with common indices

    :return : list with matched tables
    """

    common_tables = []
    for number in range(len(idx_list)):
        # Create mask where True - appropriate objects
        current_idx = idx_list[number]
        mask = np.in1d(np.array(current_idx), common_idx)

        current_object = object_list[number]
        if len(current_object.shape) == 1:
            filtered_predict = current_object[mask]
            common_tables.append(filtered_predict)
        else:
            # If the table object has many columns
            number_of_variables_in_prediction = current_object.shape[1]
            for i in range(number_of_variables_in_prediction):
                predict = current_object[:, i]
                filtered_predict = predict[mask]
                common_tables.append(filtered_predict)
    return common_tables