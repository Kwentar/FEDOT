import random

import numpy as np

from fedot.core.chains.chain_convert import chain_as_nx_graph
from fedot.core.chains.chain_validation import has_no_self_cycled_nodes
from fedot.core.composer.gp_composer.gp_composer import GPComposerRequirements
from fedot.core.composer.optimisers.adapters import DirectAdapter
from fedot.core.composer.optimisers.gp_comp.gp_optimiser import (
    GPGraphOptimiser,
    GPChainOptimiserParameters,
    GeneticSchemeTypesEnum)
from fedot.core.composer.optimisers.gp_comp.gp_optimiser import GraphGenerationParams
from fedot.core.composer.optimisers.gp_comp.operators.mutation import MutationTypesEnum
from fedot.core.composer.optimisers.gp_comp.operators.regularization import RegularizationTypesEnum
from fedot.core.dag.vertex import GraphVertex
from fedot.core.dag.graph import Graph

random.seed(1)
np.random.seed(1)


class CustomModel(Graph):
    def evaluate(self):
        return 0


def custom_metric(custom_model: CustomModel):
    _, labels = chain_as_nx_graph(custom_model)

    return [-len(labels) + custom_model.evaluate()]


def test_custom_graph_opt():
    nodes_types = ['A', 'B', 'C', 'D']
    rules = [has_no_self_cycled_nodes]

    requirements = GPComposerRequirements(
        primary=nodes_types,
        secondary=nodes_types, max_arity=3,
        max_depth=3, pop_size=5, num_of_generations=5,
        crossover_prob=0.8, mutation_prob=0.9)

    optimiser_parameters = GPChainOptimiserParameters(
        genetic_scheme_type=GeneticSchemeTypesEnum.steady_state,
        mutation_types=[
            MutationTypesEnum.simple,
            MutationTypesEnum.reduce,
            MutationTypesEnum.growth,
            MutationTypesEnum.local_growth],
        regularization_type=RegularizationTypesEnum.none)

    graph_generation_params = GraphGenerationParams(
        adapter=DirectAdapter(CustomModel),
        rules_for_constraint=rules)

    optimizer = GPGraphOptimiser(
        graph_generation_params=graph_generation_params,
        metrics=[],
        parameters=optimiser_parameters,
        requirements=requirements, initial_graph=None)

    optimized_network = optimizer.optimise(custom_metric)

    assert optimized_network is not None
    assert isinstance(optimized_network, Graph)
    assert isinstance(optimized_network.nodes[0], GraphVertex)

    assert 'A' in [str(_) for _ in optimized_network.nodes]
