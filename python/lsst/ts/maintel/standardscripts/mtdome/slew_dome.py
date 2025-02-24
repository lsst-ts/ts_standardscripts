# This file is part of ts_maintel_standardscripts
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
__all__ = ["SlewDome"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class SlewDome(salobj.BaseScript):
    """Slew main telescope dome to desired azimuth.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Slew the MTDome.",
        )

        self.mtcs = None
        self.az = None
        self.slew_time_guess = 180

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/mtdome/slew_dome.yaml
            title: SlewDome v1
            description: Configuration for SlewDome.
            type: object
            properties:
              az:
                description: Target Azimuth (in degrees) to slew the dome to.
                type: number
              ignore:
                  description: >-
                    CSCs from the group to ignore in status check. Name must
                    match those in self.group.components, e.g.; hexapod_1.
                  type: array
                  items:
                    type: string
            additionalProperties: false
            required: [az]
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
        self.az = config.az

        if self.mtcs is None:
            self.mtcs = MTCS(
                domain=self.domain, intended_usage=MTCSUsages.Slew, log=self.log
            )
            await self.mtcs.start_task

        if hasattr(self.config, "ignore"):
            self.mtcs.disable_checks_for_components(components=config.ignore)

    def set_metadata(self, metadata):
        metadata.duration = self.slew_time_guess

    async def run(self):
        await self.mtcs.enable()
        await self.mtcs.assert_all_enabled()
        self.log.info(f"Slew MT dome to Az: {self.az}.")
        await self.mtcs.slew_dome_to(az=self.az)
