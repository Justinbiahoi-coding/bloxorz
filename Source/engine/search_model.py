"""One roll per search edge; public results retain every primitive action.

Manual play still uses Bloxorz directly. The four implemented search entry
points apply this adapter, so direct calls and the solver facade agree.
"""
from functools import wraps
from time import perf_counter

from .algo_implementation.node import Node
from .problem import Bloxorz


class _RollProblem:
    """Internal graph whose actions are (roll,) or (SWITCH, roll)."""

    def __init__(self, problem):
        self.primitive = problem
        self.initial = problem.initial
        self.goal = problem.goal

    def actions(self, state):
        actions = [(a,) for a in self.primitive.actions(state) if a != 'SWITCH']
        if state.split:
            switched = self.primitive.result(state, 'SWITCH')
            actions.extend(('SWITCH', a) for a in self.primitive.actions(switched)
                           if a != 'SWITCH')
        return actions

    def steps(self, state, action):
        for primitive_action in action:
            after = self.primitive.result(state, primitive_action)
            yield state, primitive_action, after
            state = after

    def result(self, state, action):
        for _, _, state in self.steps(state, action):
            pass
        return state

    def path_cost(self, cost, state1, action, state2):
        for before, primitive_action, after in self.steps(state1, action):
            cost = self.primitive.path_cost(cost, before, primitive_action, after)
        return cost

    def goal_test(self, state):
        return self.primitive.goal_test(state)


class _PrimitiveNodes:
    """Expand each internal edge once, sharing converted parent chains by id.

    Nodes compare by state, so using Node equality as the cache key would
    incorrectly merge different paths to the same state.
    """

    def __init__(self, model):
        self.model = model
        self.converted = {}

    def convert(self, node):
        if node is None:
            return None
        pending = []
        cursor = node
        while cursor is not None and id(cursor) not in self.converted:
            pending.append(cursor)
            cursor = cursor.parent
        parent = self.converted[id(cursor)] if cursor is not None else None
        for internal in reversed(pending):
            if internal.parent is None:
                parent = Node(internal.state)
            else:
                for before, action, after in self.model.steps(parent.state, internal.action):
                    cost = self.model.primitive.path_cost(parent.path_cost, before, action, after)
                    parent = Node(after, parent, action, cost)
            self.converted[id(internal)] = parent
        return parent


def rolling_search(search):
    """Adapt Bloxorz only; leave generic Problems and search policies intact."""
    @wraps(search)
    def run(problem, *args, **kwargs):
        if not isinstance(problem, (Bloxorz, _RollProblem)):
            return search(problem, *args, **kwargs)

        started = perf_counter()
        model = _RollProblem(problem) if isinstance(problem, Bloxorz) else problem
        # solve_problem measures time and memory in separate runs. Reset here
        # so both public/direct calls include a fresh heuristic build if used.
        model.primitive.reset_heuristic_cache()
        goal, explored, _ = search(model, *args, **kwargs)
        nodes = _PrimitiveNodes(model)
        goal = nodes.convert(goal)
        # Only endpoints actually recorded by the search remain in explored.
        # Intermediate SWITCH nodes belong to paths, not extra expansions.
        explored = [nodes.convert(item) if isinstance(item, Node) else item for item in explored]
        return [goal, explored, (perf_counter() - started) * 1000]

    return run
