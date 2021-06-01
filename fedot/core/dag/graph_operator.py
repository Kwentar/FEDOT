from copy import deepcopy
from typing import Any, List, Optional

from fedot.core.dag.vertex import GraphVertex


class GraphOperator:
    def __init__(self, chain=None):
        self._chain = chain

    def delete_node(self, node: GraphVertex):
        def make_secondary_node_as_primary(node_child, new_type):
            extracted_operation = (node_child.operation.operation_type
                              if not isinstance(node_child.operation, str)
                              else node_child.operation)
            new_primary_node = new_type(operation_type=extracted_operation, nodes_from=None)
            this_node_children = self.node_children(node_child)
            for node in this_node_children:
                index = node.nodes_from.index(node_child)
                node.nodes_from.remove(node_child)
                node.nodes_from.insert(index, new_primary_node)

        node_children_cached = self.node_children(node)
        self_root_node_cached = self._chain.root_node

        for node_child in self.node_children(node):
            node_child.nodes_from.remove(node)

        if node.nodes_from and len(node_children_cached) == 1:
            for node_from in node.nodes_from:
                node_children_cached[0].nodes_from.append(node_from)
        elif not node.nodes_from:
            for node_child in node_children_cached:
                if not node_child.nodes_from:
                    make_secondary_node_as_primary(node_child, type(node))
        self._chain.nodes.clear()
        self.add_node(self_root_node_cached)

    def delete_subtree(self, node: GraphVertex):
        """Delete node with all the parents it has"""
        for node_child in self.node_children(node):
            node_child.nodes_from.remove(node)
        for subtree_node in node.ordered_subnodes_hierarchy():
            self._chain.nodes.remove(subtree_node)

    def update_node(self, old_node: GraphVertex, new_node: GraphVertex):
        self.actualise_old_node_children(old_node, new_node)
        if ((new_node.nodes_from is None and old_node.nodes_from is None) or
                (new_node.nodes_from is not None and old_node.nodes_from is not None)):
            new_node.nodes_from = old_node.nodes_from
        self._chain.nodes.remove(old_node)
        self._chain.nodes.append(new_node)
        self.sort_nodes()

    def update_subtree(self, old_node: GraphVertex, new_node: GraphVertex):
        """Exchange subtrees with old and new nodes as roots of subtrees"""
        new_node = deepcopy(new_node)
        self.actualise_old_node_children(old_node, new_node)
        self.delete_subtree(old_node)
        self.add_node(new_node)
        self.sort_nodes()

    def add_node(self, node: GraphVertex):
        """
        Add new node to the Chain

        :param node: new Node object
        """
        if node not in self._chain.nodes:
            self._chain.nodes.append(node)
            if node.nodes_from:
                for new_parent_node in node.nodes_from:
                    self.add_node(new_parent_node)

    def distance_to_root_level(self, node: GraphVertex):
        def recursive_child_height(parent_node: GraphVertex) -> int:
            node_child = self.node_children(parent_node)
            if node_child:
                height = recursive_child_height(node_child[0]) + 1
                return height
            else:
                return 0

        height = recursive_child_height(node)
        return height

    def nodes_from_layer(self, layer_number: int) -> List[Any]:
        def get_nodes(node: Any, current_height):
            nodes = []
            if current_height == layer_number:
                nodes.append(node)
            else:
                if node.nodes_from:
                    for child in node.nodes_from:
                        nodes.extend(get_nodes(child, current_height + 1))
            return nodes

        nodes = get_nodes(self._chain.root_node, current_height=0)
        return nodes

    def actualise_old_node_children(self, old_node: GraphVertex, new_node: GraphVertex):
        old_node_offspring = self.node_children(old_node)
        for old_node_child in old_node_offspring:
            index_of_old_node_in_child_nodes_from = old_node_child.nodes_from.index(old_node)
            old_node_child.nodes_from[index_of_old_node_in_child_nodes_from] = new_node

    def sort_nodes(self):
        """layer by layer sorting"""
        if not isinstance(self._chain.root_node, list):
            nodes = self._chain.root_node.ordered_subnodes_hierarchy()
        else:
            nodes = self._chain.nodes
        self._chain.nodes = nodes

    def node_children(self, node) -> List[Optional[GraphVertex]]:
        return [other_node for other_node in self._chain.nodes
                if other_node.nodes_from and
                node in other_node.nodes_from]

    def connect_nodes(self, parent: GraphVertex, child: GraphVertex):
        if child.descriptive_id not in [p.descriptive_id for p in parent.ordered_subnodes_hierarchy()]:
            if child.nodes_from:
                # if not already connected
                child.nodes_from.append(parent)
            else:
                # add parent to initial node
                new_child = GraphVertex(nodes_from=[], operation_type=child.operation)
                new_child.nodes_from.append(parent)
                self.update_node(child, new_child)

    def root_nodes(self):
        root = [node for node in self._chain.nodes
                if not any(self._chain.operator.node_children(node))]
        return root
