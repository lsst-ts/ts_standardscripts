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

__all__ = ["FocusSweepLatiss"]

import yaml
from lsst.ts.observatory.control.auxtel.atcs import ATCS
from lsst.ts.observatory.control.auxtel.latiss import LATISS, LATISSUsages
from lsst.ts.standardscripts.base_focus_sweep import BaseFocusSweep


class FocusSweepLatiss(BaseFocusSweep):
    """Perform a focus sweep by taking images at different focus positions
    with LATISS.

    Parameters
    ----------
    index : int
        Index of Script SAL component.
    """

    def __init__(self, index, descr="Perform a focus sweep with LATISS.") -> None:
        super().__init__(index=index, descr=descr)
        self.atcs = None
        self.latiss = None

        self.instrument_name = "LATISS"

    @property
    def tcs(self):
        return self.atcs

    @property
    def camera(self):
        return self.latiss

    async def configure_tcs(self) -> None:
        """Handle creating the ATCS object and waiting remote to start."""
        if self.atcs is None:
            self.log.debug("Creating ATCS.")
            self.atcs = ATCS(
                domain=self.domain,
                log=self.log,
            )
            await self.atcs.start_task
        else:
            self.log.debug("ATCS already defined, skipping.")

    async def configure_camera(self) -> None:
        """Handle creating the camera object and waiting remote to start."""
        if self.latiss is None:
            self.log.debug("Creating Camera.")
            self.latiss = LATISS(
                self.domain, intended_usage=LATISSUsages.TakeImage, log=self.log
            )
            await self.latiss.start_task
        else:
            self.log.debug("Camera already defined, skipping.")

    @classmethod
    def get_schema(cls) -> dict:
        schema_dict = super().get_schema()
        additional_properties = yaml.safe_load(
            """
            filter:
                description: Filter name or ID; if omitted the filter is not changed.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
            grating:
                description: Grating name; if omitted the grating is not changed.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
        """
        )
        schema_dict["properties"].update(additional_properties)
        return schema_dict

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        await super().configure(config=config)
        original_focus_window = self.config.focus_window
        original_focus_step_sequence = self.config.focus_step_sequence
        self.config.focus_window *= 0.001  # Transform from um to mm
        self.config.focus_step_sequence = [
            step * 0.001 for step in self.config.focus_step_sequence  # Transform to mm
        ]
        self.log.debug(
            f"""Applying unit conversion from um to mm for ATHexapod use.

        Original values in um from base class configuration are:

            focus_window = {original_focus_window} um
            focus_step_sequence = {original_focus_step_sequence} um

        Converted values:
            focus_window = {self.config.focus_window} mm
            focus_step_sequence = {self.config.focus_step_sequence} mm
        """
        )

    def get_instrument_configuration(self) -> dict:
        return dict(
            filter=self.config.filter,
            grating=self.config.grating,
        )

    def get_instrument_filter(self) -> str:
        """Get instrument filter configuration.

        Returns
        -------
        instrument_filter: `string`
        """
        filter = self.config.filter
        grating = self.config.grating
        return f"{filter}~{grating}"

    def get_instrument_name(self) -> str:
        """Get instrument name.

        Returns
        -------
        instrument_name: `string`
        """
        return self.instrument_name

    async def move_hexapod(self, axis: str, value: float) -> None:
        """Move hexapod to a position along an axis for AuxTel."""

        offset_args = {"x": 0, "y": 0, "z": 0, "u": 0, "v": 0}
        offset_args[axis] = value
        await self.atcs.offset_aos_lut(
            x=offset_args["x"],
            y=offset_args["y"],
            z=offset_args["z"],
            u=offset_args["u"],
            v=offset_args["v"],
        )
