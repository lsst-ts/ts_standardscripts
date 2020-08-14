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

__all__ = ["EnableGroup"]

import abc

from lsst.ts import salobj


class EnableGroup(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Base Script for enabling groups of CSCs.

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

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

    @property
    @abc.abstractmethod
    def group(self):
        """Return group of CSC attribute.
        """
        raise NotImplementedError()

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):
        if hasattr(self.config, "ignore"):
            for comp in self.config.ignore:
                rname = comp.lower().replace(":", "_")
                if rname not in self.group.components:
                    self.log.warning(
                        f"Component {comp} not in CSC Group. "
                        f"Must be one of {self.group.components}. Ignoring."
                    )
                else:
                    self.log.debug(f"Ignoring component {comp}.")
                    setattr(self.group.check, rname, False)

        settings = (
            dict(
                [
                    (comp, getattr(self.config, comp, ""))
                    for comp in self.group.components
                ]
            )
            if self.config is not None
            else None
        )
        await self.group.enable(settings=settings)
