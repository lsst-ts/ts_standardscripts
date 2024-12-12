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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["PrepareForCO2Cleanup"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import ATCS, ATCSUsages


class PrepareForCO2Cleanup(salobj.BaseScript):
    """Put AT in CO2 cleanup position.

    This script will slew the auxiliary telescope to the CO2 cleanup position.
    Telescope will be left in CO2 cleanup position with tracking disabled and
    mirror cover open.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Slew AT to CO2 cleanup position.",
        )

        self.atcs = None
        self.slew_time_guess = 180

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/prepare_for/co2_cleanup.yaml
            title: PrepareForCO2Cleanup v1
            description: Configuration for PrepareForCO2Cleanup.
            type: object
            properties:
                az:
                    description: Target Azimuth in degrees.
                    type: number
                    default: 0.0
                el:
                    description: Target Elevation in degrees.
                    type: number
                    minimum: 0.0
                    maximum: 90.0
                    default: 20.0
                rot_tel:
                    description: Rotator angle in mount physical coordinates (degrees).
                    type: number
                    default: 0.0
                target_name:
                    description: Name of the position.
                    type: string
                    default: "CO2 cleanup position"
                wait_dome:
                    description: Wait for dome to be in sync with the telescope?
                    type: boolean
                    default: false
                slew_timeout:
                    description: Timeout for slew procedure (in seconds).
                    type: number
                    default: 180.0
                ignore:
                    description: ATCS components to ignore in availability check.
                    type: array
                    items:
                        type: string
            additionalProperties: false
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

        if self.atcs is None:
            self.atcs = ATCS(
                domain=self.domain, intended_usage=ATCSUsages.Slew, log=self.log
            )
            await self.atcs.start_task

        if hasattr(self.config, "ignore"):
            self.atcs.disable_checks_for_components(components=config.ignore)

    def set_metadata(self, metadata):
        metadata.duration = self.slew_time_guess

    async def run(self):
        await self.atcs.assert_all_enabled()
        await self.atcs.open_m1_cover()
        await self.atcs.enable_ataos_corrections()

        self.log.debug(
            "Slew telescope to CO2 cleanup position. "
            f"Az: {self.config.az}, "
            f"El: {self.config.el}, "
            f"Rot: {self.config.rot_tel}"
        )
        await self.atcs.point_azel(
            az=self.config.az,
            el=self.config.el,
            rot_tel=self.config.rot_tel,
            target_name=self.config.target_name,
            wait_dome=self.config.wait_dome,
            slew_timeout=self.config.slew_timeout,
        )

        await self.atcs.disable_ataos_corrections()
