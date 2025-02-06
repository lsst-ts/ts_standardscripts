# This file is part of ts_standardscripts
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

__all__ = ["PrepareForOnSky"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import ATCS, LATISS, ATCSUsages, LATISSUsages


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

        self.atcs = None
        self.latiss = None

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/enable_atcs.yaml
            title: EnableATTCS v1
            description: Configuration for EnableATTCS. Only include those CSCs that are configurable.
            type: object
            properties:
                ignore:
                    description: >-
                        CSCs from the group to ignore, e.g.; atdometrajectory.
                    type: array
                    items:
                        type: string
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        # This script does not require any configuration

        if self.atcs is None:
            self.atcs = ATCS(
                self.domain, intended_usage=ATCSUsages.StartUp, log=self.log
            )
            await self.atcs.start_task

        if self.latiss is None:
            self.latiss = LATISS(
                self.domain, intended_usage=LATISSUsages.StateTransition, log=self.log
            )
            await self.latiss.start_task

        if hasattr(config, "ignore"):
            self.atcs.disable_checks_for_components(components=config.ignore)
            self.latiss.disable_checks_for_components(components=config.ignore)

    def set_metadata(self, metadata):
        metadata.duration = 600.0

    async def run(self):
        await self.atcs.assert_all_enabled(
            message="All ATCS components need to be enabled to prepare for sky observations."
        )
        await self.latiss.assert_all_enabled(
            message="All LATISS components need to be enabled to prepare for sky observations."
        )
        await self.atcs.prepare_for_onsky()
