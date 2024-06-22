# License: BSD-3-Clause
# Copyright the MNE-Python contributors.
"""WhoBPyT software for whole-brain modeling analysis."""
# PEP0440 compatible formatted version, see:
# https://www.python.org/dev/peps/pep-0440/
#
# Generic release markers:
#   X.Y
#   X.Y.Z   # For bugfix releases
#
# Admissible pre-release markers:
#   X.YaN   # Alpha release
#   X.YbN   # Beta release
#   X.YrcN  # Release Candidate
#   X.Y     # Final release
#
# Dev branch marker is: 'X.Y.devN' where N is an integer.
#

import lazy_loader as lazy

try:
    from importlib.metadata import version

    __version__ = version("whobpyt")
except Exception:
    __version__ = "0.0.0"

"""
(__getattr__, __dir__, __all__) = lazy.attach_stub(__name__, __file__)

# initialize logging
from .utils import set_log_level, set_log_file

set_log_level(None, False)
set_log_file()

"""



from . import models
from . import optimization
from . import run
from . import datasets
from . import datatypes
from . import functions
from . import visualization



