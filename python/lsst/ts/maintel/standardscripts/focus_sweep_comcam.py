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

__all__ = ["FocusSweepComCam"]

import types

import yaml
from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_focus_sweep import BaseFocusSweep


class FocusSweepComCam(BaseFocusSweep):
    """Perform a focus sweep by taking images at different focus positions
    with ComCam.

    Parameters
    ----------
    index : int
        Index of Script SAL component.
    """

    def __init__(self, index, descr="Perform a focus sweep with ComCam.") -> None:
        super().__init__(index=index, descr=descr)

        self.mtcs = None
        self.comcam = None

        self.instrument_name = "LSSTComCam"

    @property
    def tcs(self):
        return self.mtcs

    @property
    def camera(self):
        return self.comcam

    async def configure_tcs(self) -> None:
        """Handle creating the MTCS object and waiting remote to start."""
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    async def configure_camera(self) -> None:
        """Handle creating the camera object and waiting remote to start."""
        if self.comcam is None:
            self.log.debug("Creating Camera.")
            self.comcam = ComCam(
                self.domain,
                intended_usage=ComCamUsages.TakeImage | ComCamUsages.StateTransition,
                log=self.log,
            )
            await self.comcam.start_task
        else:
            self.log.debug("Camera already defined, skipping.")

    @classmethod
    def get_schema(cls) -> dict:
        schema_dict = super().get_schema()
        additional_properties = yaml.safe_load(
            """
            sim:
                description: Is ComCam in simulation mode? This mode is used for tests.
                type: boolean
                default: false
            hexapod:
                description: Which hexapod to use?
                type: string
                enum:
                    - Camera
                    - M2
                default: Camera

        """
        )
        schema_dict["properties"].update(additional_properties)
        return schema_dict

    def get_instrument_configuration(self) -> dict:
        return dict(filter=self.config.filter)

    def get_instrument_filter(self) -> str:
        return f"{self.config.filter}"

    def get_instrument_name(self) -> str:
        """Get instrument name.

        Returns
        -------
        instrument_name: `string`
        """
        return self.instrument_name

    async def move_hexapod(self, axis: str, value: float) -> None:
        """Move hexapod to a position along an axis for ComCam."""
        offset_args = {"x": 0, "y": 0, "z": 0, "u": 0, "v": 0, "w": 0}
        offset_args[axis] = value
        if self.hexapod == "Camera":
            await self.mtcs.offset_camera_hexapod(
                x=offset_args["x"],
                y=offset_args["y"],
                z=offset_args["z"],
                u=offset_args["u"],
                v=offset_args["v"],
                w=offset_args["w"],
            )
        else:
            await self.mtcs.offset_m2_hexapod(
                x=offset_args["x"],
                y=offset_args["y"],
                z=offset_args["z"],
                u=offset_args["u"],
                v=offset_args["v"],
                w=offset_args["w"],
            )

    async def configure(self, config: types.SimpleNamespace) -> None:
        await super().configure(config)
        if hasattr(config, "sim") and config.sim:
            self.comcam.simulation_mode = config.sim
            self.instrument_name += "Sim"
        self.hexapod = config.hexapod
