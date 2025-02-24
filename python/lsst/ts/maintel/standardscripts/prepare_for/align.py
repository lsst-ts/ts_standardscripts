# This file is part of ts_maintel_standardscripts
#
# Developed for the Vera Rubin Observatory.
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

__all__ = ["PrepareForAlign"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class PrepareForAlign(salobj.BaseScript):
    """Run prepare for align on MTCS.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    "Positioning telescope.": Set position at which to perform alignment.
    "Checking components...": Check all components have the right LUT.
    "MTCS Ready for...": MTCS is ready to start alignment.

    """

    def __init__(self, index: int, add_remotes: bool = True):
        super().__init__(index=index, descr="Prepare for MTCS laser tracker alignment.")

        self.config = None

        self.mtcs = MTCS(
            domain=self.domain,
            intended_usage=None if add_remotes else MTCSUsages.DryTest,
            log=self.log,
        )

    @classmethod
    def get_schema(cls):
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_externalscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/prepare_for/align.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: PrepareForAlign v1
        description: Configuration for Prepare for alignment with laser tracker.
        type: object
        properties:
            tel_align_az:
                description: telescope azimuth angle at which alignment will be performed in deg.
                type: number
                default: 0.0
                minimum: 0.0
                maximum: 360.0
            tel_align_el:
                description: telescope elevation angle at which alignment will be performed in deg.
                type: number
                default: 60.0
                minimum: 16.0
                maximum: 86.0
            tel_align_rot:
                description: telescope rotation angle at which alignment will be performed in deg.
                type: number
                default: 0.0
                minimum: 0.0
                maximum: 360.0
        additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.tel_align_az = config.tel_align_az
        self.tel_align_el = config.tel_align_el
        self.tel_align_rot = config.tel_align_rot

    def set_metadata(self, metadata):
        metadata.duration = 600.0

    async def run(self):
        """Run the script."""

        await self.checkpoint("Checking components LUT.")
        await self.mtcs.reset_m1m3_forces()
        await self.mtcs.reset_m2_forces()
        await self.mtcs.reset_camera_hexapod_position()
        await self.mtcs.reset_m2_hexapod_position()

        await self.checkpoint("Positioning Telescope.")
        await self.mtcs.point_azel(
            az=self.tel_align_az,
            el=self.tel_align_el,
            rot_tel=self.tel_align_rot,
            wait_dome=False,
        )

        await self.checkpoint("MTCS Ready for alignment.")
