from typing import Optional

import networkx as nx
from networkx.algorithms.cycles import simple_cycles
from networkx.algorithms.isolate import isolates

from fedot.core.chains.chain import Chain, chain_as_nx_graph
from fedot.core.chains.node import PrimaryNode, SecondaryNode
from fedot.core.operations.model import Model
from fedot.core.repository.tasks import Task, TaskTypesEnum
from fedot.core.repository.operation_types_repository import OperationTypesRepository

ERROR_PREFIX = 'Invalid chain configuration:'


def validate(chain: Chain, task: Optional[Task] = None):
    # TODO pass task to this function
    has_one_root(chain)
    has_no_cycle(chain)
    has_no_self_cycled_nodes(chain)
    has_no_isolated_nodes(chain)
    has_primary_nodes(chain)
    has_correct_operation_positions(chain, task)
    has_final_operation_as_model(chain)
    has_no_conflicts_with_data_flow(chain)

    # TSForecasting specific task validations
    if is_chain_contains_ts_operations(chain) is True:
        pass

    return True


def has_one_root(chain: Chain):
    if chain.root_node:
        return True


def has_no_cycle(chain: Chain):
    graph, _ = chain_as_nx_graph(chain)
    cycled = list(simple_cycles(graph))
    if len(cycled) > 0:
        raise ValueError(f'{ERROR_PREFIX} Chain has cycles')

    return True


def has_no_isolated_nodes(chain: Chain):
    graph, _ = chain_as_nx_graph(chain)
    isolated = list(isolates(graph))
    if len(isolated) > 0 and chain.length != 1:
        raise ValueError(f'{ERROR_PREFIX} Chain has isolated nodes')
    return True


def has_primary_nodes(chain: Chain):
    if not any(node for node in chain.nodes if isinstance(node, PrimaryNode)):
        raise ValueError(f'{ERROR_PREFIX} Chain does not have primary nodes')
    return True


def has_no_self_cycled_nodes(chain: Chain):
    if any([node for node in chain.nodes if isinstance(node, SecondaryNode) and node in node.nodes_from]):
        raise ValueError(f'{ERROR_PREFIX} Chain has self-cycled nodes')
    return True


def has_no_isolated_components(chain: Chain):
    graph, _ = chain_as_nx_graph(chain)
    ud_graph = nx.Graph()
    ud_graph.add_nodes_from(graph)
    ud_graph.add_edges_from(graph.edges)
    if not nx.is_connected(ud_graph):
        raise ValueError(f'{ERROR_PREFIX} Chain has isolated components')
    return True


def has_correct_operation_positions(chain: Chain, task: Optional[Task] = None):
    is_root_satisfy_task_type = True
    if task:
        is_root_satisfy_task_type = task.task_type in chain.root_node.operation.acceptable_task_types

    if not is_root_satisfy_task_type:
        raise ValueError(f'{ERROR_PREFIX} Chain has incorrect operations positions')

    return True


def has_final_operation_as_model(chain: Chain):
    """ Check if the operation in root node is model or not """
    root_node = chain.root_node

    if type(root_node.operation) is not Model:
        raise ValueError(f'{ERROR_PREFIX} Root operation is not a model')

    return True


def has_no_conflicts_with_data_flow(chain: Chain):
    """ Check if the chain contains incorrect connections between nodes """
    operation_repo = OperationTypesRepository(repository_name='data_operation_repository.json')
    forbidden_parents_combination, _ = operation_repo.suitable_operation()
    forbidden_parents_combination = set(forbidden_parents_combination)

    for node in chain.nodes:
        parent_nodes = node.nodes_from

        if parent_nodes is not None and len(parent_nodes) > 1:
            # There are several parents
            operation_names = []
            for parent in parent_nodes:
                operation_names.append(parent.operation.operation_type)

            # If operations are identical
            if len(set(operation_names)) == 1:
                # And if it is forbidden to combine them
                if operation_names[0] in forbidden_parents_combination:
                    raise ValueError(f'{ERROR_PREFIX} Chain has incorrect subgraph with identical data operations')
            else:
                # Common operations from parent nodes and forbidden repository
                common = set(operation_names) & forbidden_parents_combination
                if len(common) > 0:
                    raise ValueError(f'{ERROR_PREFIX} Chain has incorrect subgraph with wrong parent nodes combination')
    return True


def _get_ts_operations(tags=None, forbidden_tags=None, mode='all'):
    """ Function returns operations names for time series forecasting task

    :param tags: tags for grabbing when filtering
    :param forbidden_tags: tags for skipping when filtering
    :param mode: available modes 'models', 'data_operations' and 'all'
    """
    models_repo = OperationTypesRepository()
    models, _ = models_repo.suitable_operation(task_type=TaskTypesEnum.ts_forecasting,
                                               tags=tags, forbidden_tags=forbidden_tags)

    data_operations_repo = OperationTypesRepository(repository_name='data_operation_repository.json')
    data_operations, _ = data_operations_repo.suitable_operation(task_type=TaskTypesEnum.ts_forecasting,
                                                                 tags=tags, forbidden_tags=forbidden_tags)

    if mode == 'models':
        return models
    elif mode == 'data_operations':
        return data_operations
    elif mode == 'all':
        # Unit two lists
        ts_operations = models + data_operations
        return ts_operations
    else:
        raise ValueError(f'Such mode "{mode}" is not supported')


def is_chain_contains_ts_operations(chain: Chain):
    """ Function checks is the model contains operations for time series
    forecasting """
    # Get time series specific operations with tag "ts_specific"
    ts_operations = _get_ts_operations(tags=["ts_specific"], mode='all')

    # List with operations in considering chain
    operations_in_chain = []
    for node in chain.nodes:
        operations_in_chain.append(node.operation.operation_type)

    if len(set(ts_operations) & set(operations_in_chain)) > 0:
        return True
    else:
        return False


def has_no_data_flow_conflicts_in_ts_chain(chain: Chain):
    """ Function checks the correctness of connection between nodes """
    models = _get_ts_operations(mode='models')
    ts_data_operations = _get_ts_operations(mode='data_operations',
                                            forbidden_tags=["ts_specific"])

    # Dictionary as {'current operation in the node': 'parent operations list'}
    wrong_connections = {'lagged': models + ts_data_operations + ['lagged'],
                         'ar': models + ts_data_operations + ['lagged'],
                         'arima': models + ts_data_operations + ['lagged']}

    for node in chain.nodes:
        # Operation name in the current node
        current_operation = node.operation.operation_type
        parent_nodes = node.nodes_from

        if parent_nodes is not None:
            # There are several parents for current node or at least 1
            for parent in parent_nodes:
                parent_operation = parent.operation.operation_type

                forbidden_parents = wrong_connections.get(current_operation)
                if forbidden_parents is not None:
                    __check_connection(parent_operation, forbidden_parents)

    return True


def __check_connection(parent_operation, forbidden_parents):
    if parent_operation in forbidden_parents:
        raise ValueError(f'{ERROR_PREFIX} Chain has incorrect subgraph with wrong parent nodes combination')
