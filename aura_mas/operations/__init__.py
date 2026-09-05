from aura_mas.operations.store import OperationalStore

__all__ = ["OperationalApplication", "OperationalStore"]


def __getattr__(name: str):
    if name == "OperationalApplication":
        from aura_mas.operations.service import OperationalApplication
        return OperationalApplication
    raise AttributeError(name)
