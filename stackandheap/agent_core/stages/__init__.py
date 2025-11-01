import importlib, pkgutil
from .register import all_stages, get_stage_by_name
from .stage import Stage

for _, fullname, ispkg in pkgutil.iter_modules(__path__, __name__ + "."):
    if ispkg:
        importlib.import_module(fullname)