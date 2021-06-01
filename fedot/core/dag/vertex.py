from typing import Any, List, Optional

from fedot.core.dag.node_operator import NodeOperator


class GraphVertex:
    """
    Class for node definition in the DAG-based structure

    :param nodes_from: parent nodes which information comes from
    :param operation_type: str type of the operation in node
    """

    def __init__(self, nodes_from: Optional[List['GraphVertex']] = None,
                 operation_type: Any = ''):
        self.nodes_from = nodes_from
        self.operation = operation_type
        self._operator = NodeOperator(self)

    def __str__(self):
        operation = f'{self.operation}'
        return operation

    def __repr__(self):
        return self.__str__()

    @property
    def descriptive_id(self):
        return self._operator.descriptive_id()

    def ordered_subnodes_hierarchy(self, visited=None) -> List['GraphVertex']:
        return self._operator.ordered_subnodes_hierarchy(visited)

    @property
    def distance_to_primary_level(self):
        return self._operator.distance_to_primary_level()
