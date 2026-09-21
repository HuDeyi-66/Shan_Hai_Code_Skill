"""ShanHai package surface.

This repository publishes exactly one Skill package, ``skills.shanhai``. ShanHai
has no dependency on LuoHai and must not acquire one, so this package
deliberately aggregates only ShanHai.

Unlike an earlier revision, this file no longer describes a shared runtime
aggregator: ShanHai is standalone, and a runtime that integrates it does so from
its own side. The isolation guarantee is that neither Skill *package* imports the
other, and it is asserted by test.
"""

from .shanhai import *  # noqa: F401,F403
from .shanhai import __all__  # noqa: F401
