from .stage import Stage

all_stages: list[Stage] = []


def register_stage(stage: Stage) -> str:
    """ Register a stage to the global stage list.

    Args:
        stage: The stage to register.

    Returns:
        The name of the registered stage.
    """
    all_stages.append(stage)
    return stage.name


def get_stage_by_name(name: str) -> Stage:
    for stage in all_stages:
        if stage.name == name:
            return stage
    raise ValueError(f"Stage with name {name} not found.")