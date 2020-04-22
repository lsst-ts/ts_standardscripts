# This file is part of ts_standardscripts
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

__all__ = ["StandbyLATISS"]

from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.latiss import LATISS, LATISSUsages


class StandbyLATISS(salobj.BaseScript):
    """Put LATISS components in standby.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    **Details**

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):

        super().__init__(
            index=index, descr="Put all LATISS components in standby state."
        )

        self.latiss = LATISS(self.domain, intended_usage=LATISSUsages.StateTransition)

    @classmethod
    def get_schema(cls):
        # This script does not require any configuration
        return None

    async def configure(self, config):
        # This script does not require any configuration
        pass

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):

        await self.latiss.standby()
