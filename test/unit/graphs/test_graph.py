from copy import copy, deepcopy
from random import seed

import numpy as np

from fedot.core.dag.vertex import GraphVertex
from fedot.core.dag.graph import Graph
from test.unit.chains.test_chain_tuning import classification_dataset

seed(1)
np.random.seed(1)

tmp = classification_dataset


def test_graph_id():
    first = GraphVertex(operation_type='n1')
    second = GraphVertex(operation_type='n2', nodes_from=[first])
    third = GraphVertex(operation_type='n3', nodes_from=[first])
    final = GraphVertex(operation_type='n4', nodes_from=[second, third])

    assert final.descriptive_id == (
        '((/n1;)/''n2;;(/' 'n1;)/''n3;)/' 'n4')


def test_graph_str():
    # given
    first = GraphVertex(operation_type='n1')
    second = GraphVertex(operation_type='n2')
    third = GraphVertex(operation_type='n3')
    final = GraphVertex(operation_type='n4',
                        nodes_from=[first, second, third])
    graph = Graph(final)

    expected_graph_description = "{'depth': 2, 'length': 4, 'nodes': [n4, n1, n2, n3]}"

    # when
    actual_graph_description = str(graph)

    # then
    assert actual_graph_description == expected_graph_description


def test_chain_repr():
    first = GraphVertex(operation_type='n1')
    second = GraphVertex(operation_type='n2')
    third = GraphVertex(operation_type='n3')
    final = GraphVertex(operation_type='n4',
                        nodes_from=[first, second, third])
    graph = Graph(final)

    expected_graph_description = "{'depth': 2, 'length': 4, 'nodes': [n4, n1, n2, n3]}"

    assert repr(graph) == expected_graph_description


def test_delete_primary_node():
    # given
    first = GraphVertex(operation_type='n1')
    second = GraphVertex(operation_type='n2')
    third = GraphVertex(operation_type='n3', nodes_from=[first])
    final = GraphVertex(operation_type='n4', nodes_from=[second, third])
    graph = Graph(final)

    # when
    graph.delete_node(first)

    new_primary_node = [node for node in graph.nodes if node.operation == 'n2'][0]

    # then
    assert len(graph.nodes) == 3
    assert isinstance(new_primary_node, GraphVertex)


def test_graph_copy():
    chain = Graph(GraphVertex(operation_type='n1'))
    chain_copy = copy(chain)
    assert chain.uid != chain_copy.uid


def test_chain_deepcopy():
    chain = Graph(GraphVertex(operation_type='n1'))
    chain_copy = deepcopy(chain)
    assert chain.uid != chain_copy.uid
