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

__all__ = ["OfflineLATISS"]

from ..offline_group import OfflineGroup
from lsst.ts.observatory.control.auxtel.latiss import LATISS, LATISSUsages


class OfflineLATISS(OfflineGroup):
    """Put LATISS components in offline.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    None

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):

        super().__init__(
            index=index, descr="Put all LATISS components in offline state."
        )

        self._latiss = LATISS(
            self.domain, intended_usage=LATISSUsages.StateTransition, log=self.log
        )

    @property
    def group(self):
        return self._latiss

    @staticmethod
    def components():
        """Return list of components name as appeared in
        `self.group.components`.

        Returns
        -------
        components : `list` of `str`.

        """
        return {"atcamera", "atspectrograph", "atheaderservice", "atarchiver"}
