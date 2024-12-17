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
__all__ = ["SlewDome"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.atcs import ATCS


class SlewDome(salobj.BaseScript):
    """Run slew dome on ATCS.

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
        super().__init__(
            index=index,
            descr="Slew the ATDome.",
        )

        self.atcs = None

        self.az = None

    @classmethod
    def get_schema(cls):
        yaml_schema = """
            $schema: http://json-schema/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_externalscripts/auxtel/SlewDome.yaml
            title: SlewDome v1
            description: Configuration for SlewDome.
            type: object
            properties:
              az:
                description: Azimuth position (in degrees) to slew the dome to.
                type: number
            required: [az]
            additionalProperties: false
        """
        return yaml.safe_load(yaml_schema)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.log.debug(f"Configuration: {config}")

        self.az = config.az

        if self.atcs is None:
            self.atcs = ATCS(domain=self.domain, log=self.log)

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):
        self.log.info(f"Preparing to slew dome to {self.az}.")
        await self.atcs.slew_dome_to(self.az)
