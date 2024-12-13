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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.``

__all__ = ["HomeDome"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class HomeDome(salobj.BaseScript):
    """Home azimuth of the MTDome.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    Homing dome: Before commanding azimuth dome to be homed.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index=index, descr="Home MT dome.")

        self.mtcs = None
        self.physical_az = None
        self.home_dome_duration = 60.0

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/mtdome/home_dome.yaml
            title: HomeDome v1
            description: Configuration for HomeDome.
            type: object
            properties:
              physical_az:
                description: Physical azimuth position for the dome as read by markings.
                type: number
              ignore:
                  description: >-
                    CSCs from the group to ignore in status check. Name must
                    match those in self.group.components, e.g.; hexapod_1.
                  type: array
                  items:
                    type: string
            additionalProperties: false
            required: [physical_az]
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.config = config
        self.physical_az = config.physical_az

        if self.mtcs is None:
            self.mtcs = MTCS(
                domain=self.domain,
                intended_usage=MTCSUsages.Slew | MTCSUsages.StateTransition,
                log=self.log,
            )
            await self.mtcs.start_task

        if hasattr(self.config, "ignore"):
            for comp in self.config.ignore:
                if comp not in self.mtcs.components_attr:
                    self.log.warning(
                        f"Component {comp} not in CSC Group. "
                        f"Must be one of {self.mtcs.components_attr}. Ignoring."
                    )
                else:
                    self.log.debug(f"Ignoring component {comp}.")
                    setattr(self.mtcs.check, comp, False)

    def set_metadata(self, metadata):
        metadata.duration = self.home_dome_duration

    async def run(self):
        await self.mtcs.assert_all_enabled()
        await self.checkpoint("Homing dome")
        await self.mtcs.home_dome(physical_az=self.physical_az)
