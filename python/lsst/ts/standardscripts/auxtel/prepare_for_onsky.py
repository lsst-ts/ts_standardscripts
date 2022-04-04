# This file is part of ts_externalcripts
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

__all__ = ["PrepareForOnSky"]

from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import (
    ATCS,
    LATISS,
    ATCSUsages,
    LATISSUsages,
)


class PrepareForOnSky(salobj.BaseScript):
    """Run ATTCS startup.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    None

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Run ATCS startup.")

        self.config = None

        self.attcs = ATCS(self.domain, intended_usage=ATCSUsages.StartUp, log=self.log)
        self.latiss = LATISS(
            self.domain, intended_usage=LATISSUsages.StateTransition, log=self.log
        )

    @classmethod
    def get_schema(cls):
        # This script does not require any configuration
        return None

    async def configure(self, config):
        # This script does not require any configuration
        pass

    def set_metadata(self, metadata):
        metadata.duration = 600.0

    async def run(self):
        await self.attcs.assert_all_enabled(
            message="All ATCS components need to be enabled to prepare for sky observations."
        )
        await self.latiss.assert_all_enabled(
            message="All LATISS components need to be enabled to prepare for sky observations."
        )
        await self.attcs.prepare_for_onsky()
