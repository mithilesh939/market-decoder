"""
parameter_grid.py

Defines the search space for Avellaneda-Stoikov hyperparameter
optimization.

Each list represents candidate values that will be explored by the
optimization engine.
"""

from itertools import product


GAMMA_VALUES = [
    0.0001,
    0.0005,
    0.0010,
    0.0020,
]

KAPPA_VALUES = [
    0.5,
    1.0,
    1.5,
    2.0,
]

QUOTE_SIZES = [
    0.005,
    0.01,
    0.02,
]

MAX_INVENTORY = [
    0.25,
    0.50,
    1.00,
]


def parameter_grid():
    """
    Generate every parameter combination.
    """

    for gamma, kappa, quote_size, inventory_limit in product(
        GAMMA_VALUES,
        KAPPA_VALUES,
        QUOTE_SIZES,
        MAX_INVENTORY,
    ):

        yield {
            "gamma": gamma,
            "kappa": kappa,
            "quote_size": quote_size,
            "inventory_limit": inventory_limit,
        }


if __name__ == "__main__":

    configs = list(parameter_grid())

    print(f"Total strategies: {len(configs)}")

    for c in configs[:5]:
        print(c)