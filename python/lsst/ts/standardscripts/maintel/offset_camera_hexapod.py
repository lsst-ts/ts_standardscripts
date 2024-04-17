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

__all__ = ["OffsetCameraHexapod"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class OffsetCameraHexapod(salobj.BaseScript):
    """Perform a camera hexapod offset.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    **Details**

    This script can be used to either apply a user-specified offset to any of
    the Camera Hexapod axes.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Perform a camera hexapod offset",
        )

        mtcs_usage = None if add_remotes else MTCSUsages.DryTest

        self.mtcs = MTCS(domain=self.domain, intended_usage=mtcs_usage, log=self.log)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/offset_camera_hexapod.yaml
            title: OffsetCameraHexapod v1
            description: Configuration for OffsetCameraHexapod Script.
            type: object
            properties:
              x:
                type: number
                description: Offset hexapod in x axis (mm).
              y:
                type: number
                description: Offset hexapod in y axis (mm).
              z:
                type: number
                description: Offset hexapod in z axis (mm).
              u:
                type: number
                description: Rx offset (deg).
              v:
                type: number
                description: Ry offset (deg).
              sync:
                type: boolean
                default: true
                description: Synchronize hexapod movement. Default true.
              ignore:
                  description: >-
                      CSCs from the group to ignore in status check. Name must
                      match those in self.group.components, e.g.; hexapod_1.
                  type: array
                  items:
                      type: string

            additionalProperties: false
            anyOf:
                - required: ["x"]
                - required: ["y"]
                - required: ["z"]
                - required: ["u"]
                - required: ["v"]
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        self.offsets = dict(
            [(axis, getattr(config, axis, 0.0)) for axis in ["x", "y", "z", "u", "v"]]
        )

        self.sync = config.sync

        for comp in getattr(config, "ignore", []):
            if comp not in self.mtcs.components_attr:
                self.log.warning(
                    f"Component {comp} not in CSC Group. "
                    f"Must be one of {self.mtcs.components_attr}. Ignoring."
                )
            else:
                self.log.debug(f"Ignoring component {comp}.")
                setattr(self.mtcs.check, comp, False)

    def set_metadata(self, metadata):
        metadata.duration = 10

    async def assert_feasibility(self) -> None:
        """Verify that the telescope is in a feasible state to
        execute the script.
        """
        await self.mtcs.assert_all_enabled()

    async def run(self):
        await self.assert_feasibility()

        await self.checkpoint("Applying Camera Hexapod offsets...")
        await self.mtcs.offset_camera_hexapod(**self.offsets, sync=self.sync)
