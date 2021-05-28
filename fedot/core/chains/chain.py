from datetime import timedelta
from multiprocessing import Manager, Process
from typing import Callable, List, Optional, Union

from fedot.core.chains.chain_template import ChainTemplate
from fedot.core.chains.node import Node
from fedot.core.chains.tuning.unified import ChainTuner
from fedot.core.composer.cache import OperationsCache
from fedot.core.composer.optimisers.utils.population_utils import input_data_characteristics
from fedot.core.composer.timer import Timer
from fedot.core.data.data import InputData
from fedot.core.graphs.graph import GraphObject
from fedot.core.log import Log

ERROR_PREFIX = 'Invalid chain configuration:'


class Chain(GraphObject):
    """
    Base class used for composite model structure definition

    :param nodes: Node object(s)
    :param log: Log object to record messages

    .. note::
        fitted_on_data stores the data which were used in last chain fitting (equals None if chain hasn't been
        fitted yet)
    """

    def __init__(self, nodes: Optional[Union[Node, List[Node]]] = None,
                 log: Log = None):

        self.computation_time = None
        self.template = None
        self.fitted_on_data = {}
        super().__init__(nodes, log)

    def fit_from_scratch(self, input_data: InputData = None):
        """
        Method used for training the chain without using saved information

        :param input_data: data used for operation training
        """
        # Clean all saved states and fit all operations
        self.log.info('Fit chain from scratch')
        self.unfit()
        self.fit(input_data, use_fitted=False)

    def update_fitted_on_data(self, data: InputData):
        characteristics = input_data_characteristics(data=data, log=self.log)
        self.fitted_on_data['data_type'] = characteristics[0]
        self.fitted_on_data['features_hash'] = characteristics[1]
        self.fitted_on_data['target_hash'] = characteristics[2]

    def _fitted_status_if_new_data(self, new_input_data: InputData, fitted_status: bool):
        new_data_params = input_data_characteristics(new_input_data, log=self.log)
        if fitted_status and self.fitted_on_data:
            params_names = ('data_type', 'features_hash', 'target_hash')
            are_data_params_different = any(
                [new_data_param != self.fitted_on_data[param_name] for new_data_param, param_name in
                 zip(new_data_params, params_names)])
            if are_data_params_different:
                info = 'Trained operation is not actual because you are using new dataset for training. ' \
                       'Parameter use_fitted value changed to False'
                self.log.info(info)
                fitted_status = False
        return fitted_status

    def _fit_with_time_limit(self, input_data: Optional[InputData] = None, use_fitted_operations=False,
                             time: timedelta = timedelta(minutes=3)) -> Manager:
        """
        Run training process with time limit. Create

        :param input_data: data used for operation training
        :param use_fitted_operations: flag defining whether use saved information about previous executions or not,
        default True
        :param time: time constraint for operation fitting process (seconds)
        """
        time = int(time.total_seconds())
        manager = Manager()
        process_state_dict = manager.dict()
        fitted_operations = manager.list()
        p = Process(target=self._fit,
                    args=(input_data, use_fitted_operations, process_state_dict, fitted_operations),
                    kwargs={})
        p.start()
        p.join(time)
        if p.is_alive():
            p.terminate()
            raise TimeoutError(f'Chain fitness evaluation time limit is expired')

        self.fitted_on_data = process_state_dict['fitted_on_data']
        self.computation_time = process_state_dict['computation_time']
        for node_num, node in enumerate(self.nodes):
            self.nodes[node_num].fitted_operation = fitted_operations[node_num]
        return process_state_dict['train_predicted']

    def _fit(self, input_data: InputData, use_fitted_operations=False, process_state_dict: Manager = None,
             fitted_operations: Manager = None):
        """
        Run training process in all nodes in chain starting with root.

        :param input_data: data used for operation training
        :param use_fitted_operations: flag defining whether use saved information about previous executions or not,
        default True
        :param process_state_dict: this dictionary is used for saving required chain parameters (which were changed
        inside the process) in a case of operation fit time control (when process created)
        :param fitted_operations: this list is used for saving fitted operations of chain nodes
        """

        # InputData was set directly to the primary nodes
        if input_data is None:
            use_fitted_operations = False
        else:
            use_fitted_operations = self._fitted_status_if_new_data(new_input_data=input_data,
                                                                    fitted_status=use_fitted_operations)

            if not use_fitted_operations or not self.fitted_on_data:
                # Don't use previous information
                self.unfit()
                self.update_fitted_on_data(input_data)

        with Timer(log=self.log) as t:
            computation_time_update = not use_fitted_operations or not self.root_node.fitted_operation or \
                                      self.computation_time is None

            train_predicted = self.root_node.fit(input_data=input_data)
            if computation_time_update:
                self.computation_time = round(t.minutes_from_start, 3)

        if process_state_dict is None:
            return train_predicted
        else:
            process_state_dict['train_predicted'] = train_predicted
            process_state_dict['computation_time'] = self.computation_time
            process_state_dict['fitted_on_data'] = self.fitted_on_data
            for node in self.nodes:
                fitted_operations.append(node.fitted_operation)

    def fit(self, input_data: Optional[InputData] = None, use_fitted=True, time_constraint: Optional[timedelta] = None):
        """
        Run training process in all nodes in chain starting with root.

        :param input_data: data used for operation training
        :param use_fitted: flag defining whether use saved information about previous executions or not,
            default True
        :param time_constraint: time constraint for operation fitting (seconds)
        """
        if not use_fitted:
            self.unfit()

        if time_constraint is None:
            train_predicted = self._fit(input_data=input_data, use_fitted_operations=use_fitted)
        else:
            train_predicted = self._fit_with_time_limit(input_data=input_data, use_fitted_operations=use_fitted,
                                                        time=time_constraint)
        return train_predicted

    @property
    def is_fitted(self):
        return all([(node.fitted_operation is not None) for node in self.nodes])

    def unfit(self):
        """
        Remove fitted operations for all nodes.
        """
        for node in self.nodes:
            node.unfit()

    def fit_from_cache(self, cache: OperationsCache):
        for node in self.nodes:
            cached_state = cache.get(node)
            if cached_state:
                node.fitted_operation = cached_state.operation
            else:
                node.fitted_operation = None

    def predict(self, input_data: InputData = None, output_mode: str = 'default'):
        """
        Run the predict process in all nodes in chain starting with root.

        :param input_data: data for prediction
        :param output_mode: desired form of output for operations. Available options are:
                'default' (as is),
                'labels' (numbers of classes - for classification) ,
                'probs' (probabilities - for classification =='default'),
                'full_probs' (return all probabilities - for binary classification).
        :return: OutputData with prediction
        """

        if not self.is_fitted:
            ex = 'Trained operation is not actual or empty'
            self.log.error(ex)
            raise ValueError(ex)

        result = self.root_node.predict(input_data=input_data, output_mode=output_mode)
        return result

    def fine_tune_all_nodes(self, loss_function: Callable,
                            loss_params: Callable = None,
                            input_data: Optional[InputData] = None,
                            iterations=50, max_lead_time: int = 5) -> 'Chain':
        """ Tune all hyperparameters of nodes simultaneously via black-box
            optimization using ChainTuner. For details, see
        :meth:`~fedot.core.chains.tuning.unified.ChainTuner.tune_chain`
        """
        max_lead_time = timedelta(minutes=max_lead_time)
        chain_tuner = ChainTuner(chain=self,
                                 task=input_data.task,
                                 iterations=iterations,
                                 max_lead_time=max_lead_time)
        self.log.info('Start tuning of primary nodes')
        tuned_chain = chain_tuner.tune_chain(input_data=input_data,
                                             loss_function=loss_function,
                                             loss_params=loss_params)
        self.log.info('Tuning was finished')

        return tuned_chain

    def save(self, path: str):
        """
        Save the chain to the json representation with pickled fitted operations.

        :param path to json file with operation
        :return: json containing a composite operation description
        """
        if not self.template:
            self.template = ChainTemplate(self, self.log)
        json_object = self.template.export_chain(path)
        return json_object

    def load(self, path: str):
        """
        Load the chain the json representation with pickled fitted operations.

        :param path to json file with operation
        """
        self.nodes = []
        self.template = ChainTemplate(self, self.log)
        self.template.import_chain(path)

    def __eq__(self, other) -> bool:
        return self.root_node.descriptive_id == other.root_node.descriptive_id

    def __str__(self):
        description = {
            'depth': self.depth,
            'length': self.length,
            'nodes': self.nodes,
        }
        return f'{description}'

    @property
    def root_node(self) -> Optional[Node]:
        if len(self.nodes) == 0:
            return None
        root = [node for node in self.nodes
                if not any(self.operator.node_children(node))]
        if len(root) > 1:
            raise ValueError(f'{ERROR_PREFIX} More than 1 root_nodes in chain')
        return root[0]
