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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["OffsetM2Hexapod"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class OffsetM2Hexapod(salobj.BaseScript):
    """Perform a m2 hexapod offset or reset operation..

    This script allows for precise control over the M2 Hexapod by either
    applying user-specified offsets to its axes and/or resetting the position
    of specified axes.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Details**

    This script can be used to either apply a user-specified offset to any of
    the M2 Hexapod axes or to reset the position of the provided axes. It
    can either reset the positions before applying the offsets or just apply
    a reset without applying offsets.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Perform a M2 hexapod offset or reset the position of the provided axes.",
        )

        mtcs_usage = None if add_remotes else MTCSUsages.DryTest

        self.mtcs = MTCS(domain=self.domain, intended_usage=mtcs_usage, log=self.log)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/offset_m2_hexapod.yaml
            title: OffsetM2Hexapod v1
            description: Configuration for OffsetM2Hexapod Script.
            type: object
            properties:
              x:
                type: number
                description: Offset hexapod in x axis (micron).
              y:
                type: number
                description: Offset hexapod in y axis (micron).
              z:
                type: number
                description: Offset hexapod in z axis (micron).
              u:
                type: number
                description: Rx offset (deg).
              v:
                type: number
                description: Ry offset (deg).
              reset_axes:
                default: false
                oneOf:
                  - type: boolean
                    description: >-
                      If true, resets the axes provided in the offsets before applying the offsets.
                      If false or not provided, no reset is performed.
                  - type: string
                    enum: ["all"]
                    description: Reset all axes.
                  - type: array
                    items:
                      minItems: 1
                      type: string
                      enum: ["x", "y", "z", "u", "v"]
                    description: List of axes to reset.
                description: >-
                  Axes to reset before applying offsets. Use true to reset axes provided in offsets,
                  "all" to reset all axes, or a list of axes to reset specific axes. Default is false.
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
              - required: ["reset_axes"]
              - anyOf:
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

        Raises
        ------
        ValueError
            If neither non-zero offsets nor a reset operation is provided
            in the configuration.

            If reset_axes is set to true, but no non-zero axis offsets
            are provided to reset.
        """

        # Initialize offsets with 0.0
        self.offsets = {
            axis: getattr(config, axis, 0.0) for axis in ["x", "y", "z", "u", "v"]
        }

        self.sync = config.sync

        # Handle reset_axes
        self.reset_axes = []
        reset_axes_config = getattr(config, "reset_axes", False)
        if reset_axes_config is True:
            # Reset axes provided in the offsets
            self.reset_axes = [
                axis for axis, value in self.offsets.items() if value != 0.0
            ]
            if not self.reset_axes:
                raise ValueError(
                    "reset_axes is set to true, but no non-zero axis offsets are provided to reset."
                )
        elif reset_axes_config == "all":
            self.reset_axes = ["x", "y", "z", "u", "v"]
        elif isinstance(reset_axes_config, list):
            self.reset_axes = reset_axes_config

        # Validate configuration
        offsets_provided = any(value != 0.0 for value in self.offsets.values())
        reset_operation = bool(self.reset_axes)

        if not offsets_provided and not reset_operation:
            raise ValueError(
                "Configuration must provide at least one non-zero axis offset or a reset operation."
            )

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

        # Perform reset operation if specified
        if self.reset_axes:
            reset_values = {axis: 0.0 for axis in self.reset_axes}
            await self.checkpoint(
                f"Resetting the following axes: {list(reset_values.keys())}"
            )
            await self.mtcs.move_m2_hexapod(**reset_values, sync=self.sync)

        # Dictionary with offsets to apply
        offsets_to_apply = {axis: 0.0 for axis in ["x", "y", "z", "u", "v"]}
        offsets_to_apply.update(
            {axis: value for axis, value in self.offsets.items() if value != 0.0}
        )

        # Check if at least one value in offsets_to_apply is not zero
        if any(offsets_to_apply.values()):
            await self.checkpoint(
                f"Applying M2 Hexapod offsets to the following axes: {list(offsets_to_apply.keys())}."
            )
            await self.mtcs.offset_m2_hexapod(**offsets_to_apply, sync=self.sync)
