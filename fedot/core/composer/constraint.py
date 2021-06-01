from typing import Optional

from fedot.core.chains.chain_validation import custom_validate, validate
from fedot.core.composer.optimisers.graph import OptGraph


def constraint_function(graph: OptGraph,
                        params: Optional['GraphGenerationParams'] = None):
    try:
        if not params or params.rules_for_constraint is None:
            chain = params.adapter.restore(graph)
            validate(chain)
        else:
            custom_validate(graph, params.rules_for_constraint)
        return True
    except ValueError:
        return False
