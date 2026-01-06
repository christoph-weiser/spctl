# SPCTL - Spice Control
# Copyright (C) 2024 Christoph Weiser
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
try:
    SIMULATOR = os.environ["SIMULATOR"]
except(KeyError):
    SIMULATOR = "ngspice"
    
from .optimize import *
from .helpers import *
from .regression import *

if SIMULATOR == "ngspice":
    from .ngspice  import *
elif SIMULATOR == "xyce":
    from .xyce import *
else:
    raise exception("simulator not recognized.")
