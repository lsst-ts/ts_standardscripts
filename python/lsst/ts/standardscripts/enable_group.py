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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["EnableGroup"]

import abc

from lsst.ts import salobj


class EnableGroup(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Base Script for enabling groups of CSCs.

    This base class is setup to operate with minimum configuration. By default
    it will try to access an attribute `self.config.ignore`, which is supposed
    to contain a list of CSCs from the group to be ignored in the process.
    The name of the CSC must match the name of the CSC in `group.components`,
    which is the name of the CSC in lowercase, replacing the ":" with "_" for
    indexed components. For example,

        * ATMCS -> atmcs
        * NewMTMount -> newmtmount
        * Hexapod:1 -> hexapod_1

    For instance, if one wants to ignore the MTDomeTrajectory and the Hexapod:1
    (Hexapod with index=1) components from the MTCS the ignore field would look
    like:

        ignore:
            - mtdometrajectory
            - hexapod_1

    Nevertheless, if the parent class does not provide an `ignore` property the
    class will skip it.

    In addition, when subclassing this base class, users can provide settings
    for the configurable CSCs in the group. The naming *must* also follow the
    same guidelines as for the ignore field, matching the value in
    `group.components`. Following the example above, to pass in the labels
    `special_configuration` and `lut_with_temperature` to configure the
    MTDomeTrajectory and Hexapod:1, respectively, one would do;

        mtdometrajectory: special_configuration
        hexapod_1: lut_with_temperature


    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    descr : `str`
        Short Script description.

    Notes
    -----

    **Checkpoints**

    None

    **Details**

    All CSCs will be enabled concurrently.

    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

    @property
    @abc.abstractmethod
    def group(self):
        """Return group of CSC attribute.

        Returns
        -------
        group
            This property must return a subclass of `RemoteGroup` from
            `lsst.ts.observatory.control`, e.g. `ATCS` or `MTCS`.

        """
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def components():
        """Return list of components name as appeared in
        `self.group.components`.

        Returns
        -------
        components : `list` of `str`.

        """
        raise NotImplementedError()

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):
        if hasattr(self.config, "ignore"):
            self.group.disable_checks_for_components(components=self.config.ignore)

        overrides = (
            dict([(comp, getattr(self.config, comp, "")) for comp in self.components()])
            if self.config is not None
            else None
        )
        await self.group.enable(overrides=overrides)
