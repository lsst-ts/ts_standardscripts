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

__all__ = ["TakeTripletComCam"]

import asyncio
import types

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS

from ..base_block_script import BaseBlockScript


class TakeTripletComCam(BaseBlockScript):
    """Take triplet (intra-focal, extra-focal and in-focus images)
    sequence with ComCam.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * triplet {n} of {m}: before taking a triplet.

    """

    def __init__(self, index, descr="Take triplet with ComCam.") -> None:
        super().__init__(index=index, descr=descr)

        self.config = None
        self.mtcs = None
        self.camera = None

    @classmethod
    def get_schema(cls) -> dict:
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/TakeTripletComCam.yaml
            title: TakeTripletComCam v1
            description: Configuration for TakeTripletComCam.
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
              exposure_time:
                description: The exposure time to use when taking images (sec).
                type: number
                default: 30.
              dz:
                description: De-focus to apply when acquiring the intra/extra focal images (microns).
                type: number
                default: 1500.
              n_triplets:
                description: Number of triplets.
                type: integer
                default: 1
              program:
                description: >-
                    Optional name of the program this dataset belongs to.
                type: string
                default: TRIPLET
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
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        # Configure tcs and camera
        await self.configure_tcs()
        await self.configure_camera()

        if hasattr(config, "ignore"):
            for comp in config.ignore:
                if comp in self.mtcs.components_attr:
                    self.log.debug(f"Ignoring MTCS component {comp}.")
                    setattr(self.mtcs.check, comp, False)
                elif comp in self.camera.components_attr:
                    self.log.debug(f"Ignoring Camera component {comp}.")
                    setattr(self.camera.check, comp, False)
                else:
                    self.log.warning(
                        f"Component {comp} not in CSC Groups. "
                        f"Must be one of {self.mtcs.components_attr} or "
                        f"{self.camera.components_attr}. Ignoring."
                    )

        # Set filter
        self.filter = config.filter

        # Set exposure time
        self.exposure_time = config.exposure_time

        # Set intra/extra focal offsets
        self.dz = config.dz

        # Set maximum number of iterations
        self.n_triplets = config.n_triplets

        # Set program and reason
        self.reason = config.reason
        self.program = config.program

    def set_metadata(self, metadata: salobj.type_hints.BaseMsgType) -> None:
        """Sets script metadata.

        Parameters
        ----------
        metadata : `salobj.type_hints.BaseMsgType`
            Script metadata topic. The information is set on the topic
            directly.
        """
        # Estimated duration is maximum number of iterations multiplied by
        # 3 (data triplet) multiplied by the time it takes to take an image
        # plus estimation on reading out the images (10s)

        metadata.duration = (
            self.n_triplets
            * 3
            * (
                self.exposure_time
                + self.camera.read_out_time
                + self.camera.shutter_time
            )
        )
        metadata.filter = f"{self.filter}"

    async def assert_feasibility(self) -> None:
        """Verify that the telescope and camera are in a feasible state to
        execute the script.
        """
        await asyncio.gather(
            self.mtcs.assert_all_enabled(), self.camera.assert_all_enabled()
        )

    async def configure_camera(self) -> None:
        """Handle creating ComCam object and waiting for remote to start."""
        if self.camera is None:
            self.log.debug("Creating Camera.")

            self.camera = ComCam(
                self.domain, log=self.log, intended_usage=ComCamUsages.TakeImage
            )
            await self.camera.start_task
        else:
            self.log.debug("Camera already defined, skipping.")

    async def configure_tcs(self) -> None:
        """Handle creating MTCS object and waiting for remote to start."""
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    async def take_triplet(
        self,
    ) -> None:
        """Take triplet (intra focal, extra focal and in-focus)
        image sequence.
        """
        self.log.debug("Moving to intra-focal position")

        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=self.dz, u=0, v=0)

        self.log.info("Taking intra-focal image")

        await self.camera.take_cwfs(
            exptime=self.exposure_time,
            n=1,
            group_id=self.group_id,
            filter=self.filter,
            reason="INTRA" + ("" if self.reason is None else f"_{self.reason}"),
            program=self.program,
        )

        self.log.debug("Moving to extra-focal position")

        # Hexapod offsets are relative, so need to move 2x the offset
        # to get from the intra- to the extra-focal position.
        z_offset = -(self.dz * 2.0)
        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)

        self.log.info("Taking extra-focal image")

        await self.camera.take_cwfs(
            exptime=self.exposure_time,
            n=1,
            group_id=self.group_id,
            filter=self.filter,
            reason="EXTRA" + ("" if self.reason is None else f"_{self.reason}"),
            program=self.program,
        )

        self.log.debug("Moving to in-focus position")

        # Move the hexapod back to in focus position
        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=self.dz, u=0, v=0)

        self.log.info("Taking in-focus image")

        await self.camera.take_acq(
            exptime=self.exposure_time,
            n=1,
            group_id=self.group_id,
            filter=self.filter,
            reason="INFOCUS" + ("" if self.reason is None else f"_{self.reason}"),
            program=self.program,
        )

    async def run_block(self) -> None:
        """Execute script operations."""
        await self.assert_feasibility()

        for i in range(self.n_triplets):
            self.log.info(f"Starting triplet {i+1} of {self.n_triplets}")
            await self.checkpoint(f"triplet {i+1} of {self.n_triplets}")

            await self.take_triplet()
