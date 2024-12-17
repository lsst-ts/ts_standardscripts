#!/usr/bin/env python
# This file is part of ts_auxtel_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.Scheduler import SalIndex
from lsst.ts.standardscripts.scheduler import SetDesiredState


class ATSchedulerStandby(SetDesiredState):
    """Send ATScheduler to STANDBY state."""

    def __init__(self, index: int) -> None:
        super().__init__(
            index,
            desired_state=salobj.State.STANDBY,
            descr="Send AuxTel Scheduler to standby state",
            scheduler_index=SalIndex.AUX_TEL,
        )


asyncio.run(ATSchedulerStandby.amain())
