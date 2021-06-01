from abc import abstractmethod
from typing import Any, Type

from fedot.core.chains.chain import Chain
from fedot.core.chains.node import PrimaryNode, SecondaryNode, GraphVertex
from fedot.core.composer.optimisers.graph import OptGraph


class BaseOptimizationAdapter:
    def __init__(self, base_class: Type, log=None):
        """
        Base class for for the optimization adapter
        """
        self._log = log
        self._base_class = base_class

    @abstractmethod
    def adapt(self, adaptee: Any):
        raise NotImplementedError()

    @abstractmethod
    def restore(self, opt_graph: OptGraph):
        raise NotImplementedError()


class DirectAdapter(BaseOptimizationAdapter):
    def adapt(self, adaptee: Any):
        opt_graph = adaptee
        opt_graph.__class__ = OptGraph
        return opt_graph

    def restore(self, opt_graph: OptGraph):
        obj = opt_graph
        opt_graph.__class__ = self._base_class
        return obj


class ChainAdapter(BaseOptimizationAdapter):
    def __init__(self, log=None):
        """
        Optimization adapter for Chain class
        """
        super().__init__(base_class=Chain, log=log)

    def adapt(self, adaptee: Chain):
        opt_nodes = []
        for node in adaptee.nodes:
            node.__class__ = GraphVertex
            opt_nodes.append(node)
        return OptGraph(opt_nodes)

    def restore(self, opt_graph: OptGraph):
        chain_nodes = []
        for node in opt_graph.nodes:
            if node.nodes_from is None:
                node.__class__ = PrimaryNode
                node.__init__(operation_type=node.operation)
            else:
                node.__class__ = SecondaryNode
                node.__init__(nodes_from=node.nodes_from,
                              operation_type=node.operation)

            chain_nodes.append(node)
        return Chain(chain_nodes)
