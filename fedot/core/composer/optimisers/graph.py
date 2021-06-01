from typing import Any, List, Optional, Union

from fedot.core.dag.vertex import GraphVertex
from fedot.core.dag.graph import Graph
from fedot.core.log import Log, default_log


class OptGraph(Graph):
    """
    Base class used for optimized structure

    :param nodes: OptNode object(s)
    :param log: Log object to record messages
    """

    def __init__(self, nodes: Optional[Union[GraphVertex, List[GraphVertex]]] = None,
                 log: Log = None):
        self.log = log
        if not log:
            self.log = default_log(__name__)
        else:
            self.log = log
        super().__init__(nodes)


class OptNode(GraphVertex):
    """
    Class for node definition in the structure for optimization

    :param nodes_from: parent nodes
    :param operation_type: str type of the operation in node
    """

    def __init__(self, nodes_from: Optional[List['OptNode']] = None,
                 operation_type: str = '', log: Optional[Log] = None):
        self.log = log
        if not log:
            self.log = default_log(__name__)
        else:
            self.log = log
        super().__init__(nodes_from, operation_type)
