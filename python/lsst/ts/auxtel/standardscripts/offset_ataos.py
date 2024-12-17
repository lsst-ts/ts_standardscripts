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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["OffsetATAOS"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import ATCS, ATCSUsages


class OffsetATAOS(salobj.BaseScript):
    """Perform an ATAOS offset.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Clearing ATAOS offsets...": Before clearing ATAOS offsets if configured.
    - "Applying ATAOS offsets...": Before applying ATAOS offsets if configured.

    **Details**

    This script can be used to either apply a user-specified offset to any of
    the ATAOS axes or clear the current offsets.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Perform an ATCS offset",
        )

        atcs_usage = None if add_remotes else ATCSUsages.DryTest

        self.atcs = ATCS(domain=self.domain, intended_usage=atcs_usage, log=self.log)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/offset_atcs.yaml
            title: OffsetATCS v1
            description: Configuration for OffsetATCS Script.
            type: object
            properties:
              z:
                type: number
                description: Offset hexapod in z axis (mm).
              x:
                type: number
                description: Offset hexapod in x axis (mm).
              y:
                type: number
                description: Offset hexapod in y axis (mm).
              u:
                type: number
                description: Rx offset (deg).
              v:
                type: number
                description: Ry offset (deg).
              m1:
                type: number
                description: M1 pressure offset (Pa).
                maximum: 0
              offset_telescope:
                type: bool
                description: When correcting coma, also offset the telescope?
                type: boolean
                default: true
              reset_offsets:
                description: >-
                    List of axes to reset or all. List of axes must contain
                    at least one of "x", "y", "z", "u", "v", or "m1"
                oneOf:
                    -
                        type: array
                        minItems: 1
                        uniqueItems: true
                        items:
                            type: string
                            enum: ["z", "x", "y", "u", "v", "m1"]
                    -
                        type: string
                        enum: ["all"]

            additionalProperties: false
            anyOf:
                - required: ["z"]
                - required: ["x"]
                - required: ["y"]
                - required: ["u"]
                - required: ["v"]
                - required: ["m1"]
                - required: ["reset_offsets"]
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        self.reset_offsets = getattr(config, "reset_offsets", None)

        if self.reset_offsets == "all":
            self.reset_offsets = ["z", "x", "y", "u", "v", "m1"]

        self.offset_telescope = config.offset_telescope

        self.offsets = dict(
            [
                (axis, getattr(config, axis, 0.0))
                for axis in ["x", "y", "z", "u", "v", "m1"]
            ]
        )

    def set_metadata(self, metadata):
        metadata.duration = 10

    async def assert_feasibility(self) -> None:
        """Verify that the telescope is in a feasible state to
        execute the script.
        """

        await self.atcs.assert_all_enabled()
        await self.atcs.assert_ataos_corrections_enabled()

    async def run(self):
        await self.assert_feasibility()

        if self.reset_offsets is not None:
            await self.checkpoint("Clearing ATAOS offsets...")
            for axis in self.reset_offsets:
                self.log.info(f"Clearing offsets in axes: {axis}")
                await self.atcs.rem.ataos.cmd_resetOffset.set_start(
                    axis=axis, timeout=self.atcs.long_timeout
                )

        else:
            await self.checkpoint("Applying ATAOS offsets...")
            await self.atcs.offset_aos_lut(
                **self.offsets, offset_telescope=self.offset_telescope
            )
