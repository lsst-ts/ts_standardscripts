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

__all__ = ["BaseStopTracking"]

import abc

from lsst.ts import salobj


class BaseStopTracking(salobj.BaseScript):
    """A base script that implements stop_tracking functionality for `BaseTCS`
    classes.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    Stop tracking: Before issuing stop tracking.
    Done: After issuing stop tracking.
    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        pass

    def set_metadata(self, metadata):
        metadata.duration = self.tcs.tel_settle_time

    async def run(self):
        await self.checkpoint("Stop tracking")
        await self.tcs.stop_tracking()
        await self.checkpoint("Done")
