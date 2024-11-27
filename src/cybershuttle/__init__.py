from __future__ import annotations

from . import auth, base, md, plan, runtime


def task_context(task: base.Task):
    def inner(func):
        # take the function into the task's location
        # and execute it there. then fetch the result
        result = func(**task.inputs)
        # and return it to the caller.
        return result

    return inner


__all__ = ["auth", "base", "md", "plan", "runtime", "task_context"]
