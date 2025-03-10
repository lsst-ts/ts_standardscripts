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

__all__ = ["BaseFocusSweep"]

import abc
import asyncio
import json
import types

import yaml
from lsst.ts import salobj

from .base_block_script import BaseBlockScript


class BaseFocusSweep(BaseBlockScript):
    """Perform a focus sweep by taking images at different focus positions.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * Step 1/n_steps axis: axis starting position: start_position.
    * Step n/n_steps axis: axis.
    """

    def __init__(self, index, descr="Perform a focus sweep.") -> None:
        super().__init__(index=index, descr=descr)

        self.ocps = None

        self.config = None

        self.total_focus_offset = 0.0
        self.iterations_started = False
        self.focus_visit_ids = []

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def configure_tcs(self):
        """Abstract method to configure the TCS."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def camera(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def configure_camera(self):
        """Abstract method to configure the Camera."""
        raise NotImplementedError()

    async def configure_ocps(self):
        """Configure the OCPS remote object."""
        if self.ocps is None:
            self.log.debug("Configuring remote for OCPS:101")
            self.ocps = salobj.Remote(self.domain, "OCPS", 101)
            await self.ocps.start_task
        else:
            self.log.debug("OCPS already configured. Ignoring.")

    @classmethod
    def get_schema(cls) -> dict:
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/base_focus_sweep.yaml
            title: BaseFocusSweep v1
            description: Configuration for BaseFocusSweep.
            type: object
            properties:
              filter:
                description: Filter name or ID; if omitted the filter is not changed.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
              exp_time:
                description: The exposure time to use when taking images (sec).
                type: number
                default: 10.
              axis:
                description: Axis to perform the focus sweep. Should be one of "x", "y", "z", "u" and "v".
                type: string
                enum: ["x", "y", "z", "u", "v"]
              focus_window:
                description: Total range (window) measured in um for the focus sweep.
                type: number
              n_steps:
                description: Number of steps to take inside the focus window.
                type: number
                minimum: 2
              focus_step_sequence:
                description: >-
                    User-provided sequence of focus steps measured in um to take for the focus sweep,
                    used for unevenly spaced steps.
                type: array
                items:
                  type: number
                minItems: 2
              n_images_per_step:
                description: Number of images to take at each focus position.
                type: integer
                default: 1
              program:
                description: >-
                    Optional name of the program this dataset belongs to.
                type: string
                default: FOCUS_SWEEP
              reason:
                description: Optional reason for taking the data.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              ignore:
                description: >-
                    CSCs from the group to ignore in status check. Name must
                    match those in self.group.components, e.g.; hexapod_1.
                type: array
                items:
                  type: string
            oneOf:
                - required:
                    - axis
                    - focus_window
                    - n_steps
                - required:
                    - axis
                    - focus_step_sequence
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        await self.configure_tcs()
        await self.configure_camera()
        await self.configure_ocps()

        if hasattr(config, "ignore"):
            self.log.debug("Ignoring TCS components.")
            self.tcs.disable_checks_for_components(components=config.ignore)
            self.log.debug("Ignoring Camera components.")
            self.camera.disable_checks_for_components(components=config.ignore)

        if hasattr(config, "focus_step_sequence"):
            config.focus_window = (
                config.focus_step_sequence[-1] - config.focus_step_sequence[0]
            )
            config.n_steps = len(config.focus_step_sequence)
        elif hasattr(config, "focus_window"):
            config.focus_step_sequence = [
                i * config.focus_window / (config.n_steps - 1)
                for i in range(config.n_steps)
            ]
            config.focus_step_sequence = [
                s - config.focus_window * 0.5 for s in config.focus_step_sequence
            ]

        self.config = config

        await super().configure(config=config)

    def set_metadata(self, metadata: salobj.type_hints.BaseMsgType) -> None:
        """Sets script metadata.

        Parameters
        ----------
        metadata : `salobj.type_hints.BaseMsgType`
            Script metadata topic.
        """

        metadata.duration = (
            self.config.n_steps
            * self.config.n_images_per_step
            * (
                self.config.exp_time
                + self.camera.read_out_time
                + self.camera.shutter_time
            )
        )

        metadata.instrument = self.get_instrument_name()
        metadata.filter = self.get_instrument_filter()

    async def assert_feasibility(self) -> None:
        """Verify that the telescope and camera are in a feasible state to
        execute the script.
        """
        await asyncio.gather(
            self.tcs.assert_all_enabled(), self.camera.assert_all_enabled()
        )

    async def focus_sweep(self) -> None:
        """Perform the focus sweep operation."""

        axis = self.config.axis

        start_position = self.config.focus_step_sequence[0]

        offset_display_value = (
            f"{start_position:+0.2} um"
            if axis in "xyz"
            else f"{start_position*60.*60.:+0.2} arcsec"
        )

        await self.checkpoint(
            f"Step 1/{self.config.n_steps} {axis=} starting position: {offset_display_value}."
        )
        self.log.info("Offset hexapod to starting position.")
        await self.move_hexapod(axis, start_position)
        self.total_focus_offset += start_position
        self.iterations_started = True

        visit_ids = await self.camera.take_focus(
            exptime=self.config.exp_time,
            n=self.config.n_images_per_step,
            group_id=self.group_id,
            program=self.program,
            reason=self.reason,
            note=f"Focus Sweep Camera d{axis.upper()} {offset_display_value}",
            **self.get_instrument_configuration(),
        )

        self.focus_visit_ids.extend(visit_ids)

        try:
            for self.iterations_executed in range(1, self.config.n_steps):
                await self.checkpoint(
                    f"Step {self.iterations_executed+1}/{self.config.n_steps} {axis=}."
                )
                hexapod_offset = (
                    self.config.focus_step_sequence[self.iterations_executed]
                    - self.config.focus_step_sequence[self.iterations_executed - 1]
                )
                await self.move_hexapod(axis, hexapod_offset)
                self.total_focus_offset += hexapod_offset
                offset_display_value = (
                    f"{self.total_focus_offset:+0.2} um"
                    if axis in "xyz"
                    else f"{self.total_focus_offset*60.*60.:+0.2} arcsec"
                )
                visit_ids = await self.camera.take_focus(
                    exptime=self.config.exp_time,
                    n=self.config.n_images_per_step,
                    group_id=self.group_id,
                    program=self.program,
                    reason=self.reason,
                    note=f"Focus Sweep Camera d{axis.upper()} {offset_display_value}",
                    **self.get_instrument_configuration(),
                )

                self.focus_visit_ids.extend(visit_ids)
        finally:

            if len(self.focus_visit_ids) > 2:

                instrument = self.get_instrument_name()
                config = {
                    f"{instrument}-FROM-OCS_FOCUSSWEEP": ",".join(
                        [str(visit_id) for visit_id in self.focus_visit_ids]
                    )
                }

                self.log.info("Starting focus sweep pipeline.")
                try:
                    await self.ocps.cmd_execute.set_start(
                        config=json.dumps(config),
                        timeout=self.camera.fast_timeout,
                    )
                except Exception:
                    self.log.exception(
                        "Failed to execute focus sweep through OCPS. Ignoring."
                    )
            else:
                self.log.warning(
                    "Not enough exposures taken to process focus sweep. Ignoring."
                )

    @abc.abstractmethod
    async def move_hexapod(self, axis: str, value: float) -> None:
        """Move hexapod to a specific position along a specified axis."""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_instrument_configuration(self) -> dict:
        """Get the instrument configuration.

        Returns
        -------
        dict
            Dictionary with instrument configuration.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_instrument_filter(self) -> str:
        """Get the instrument filter configuration.

        Returns
        -------
        str
            Instrument filter configuration.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_instrument_name(self) -> str:
        raise NotImplementedError()

    async def run_block(self) -> None:
        """Execute script operations."""

        await self.assert_feasibility()
        await self.focus_sweep()

    async def cleanup(self):
        try:
            if self.iterations_started:

                self.log.info(
                    f"Returning hexapod to original position by moving "
                    f"{self.total_focus_offset} back along axis {self.config.axis}."
                )
                await self.move_hexapod(self.config.axis, -self.total_focus_offset)
        except Exception:
            self.log.exception(
                "Error while trying to return hexapod to its original position."
            )
