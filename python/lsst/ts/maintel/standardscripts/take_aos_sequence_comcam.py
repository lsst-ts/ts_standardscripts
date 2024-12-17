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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["TakeAOSSequenceComCam", "Mode"]

import asyncio
import enum
import json
import types

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.comcam import ComCam
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class Mode(enum.IntEnum):
    TRIPLET = enum.auto()
    INTRA = enum.auto()
    EXTRA = enum.auto()
    PAIR = enum.auto()


class TakeAOSSequenceComCam(BaseBlockScript):
    """Take aos sequence, either triplet (intra-focal, extra-focal
    and in-focus images), intra doublets (intra and in-focus) or extra
    doublets (extra and in-focus) sequences with ComCam.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * sequence {n} of {m}: before taking a sequence.

    """

    def __init__(self, index, descr="Take AOS sequence with ComCam.") -> None:
        super().__init__(index=index, descr=descr)

        self.config = None
        self.mtcs = None
        self.camera = None
        self.ocps = None
        self.current_z_position = 0
        self.n_images = 9

    @classmethod
    def get_schema(cls) -> dict:
        schema_yaml = f"""
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/TakeAOSSequenceComCam.yaml
            title: TakeAOSSequenceComCam v1
            description: Configuration for TakeAOSSequenceComCam.
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
              n_sequences:
                description: Number of aos sequences.
                type: integer
                default: 1
              mode:
                description: >-
                    Mode of operation. Options are 'triplet' (default), 'intra' or 'extra'.
                type: string
                default: TRIPLET
                enum: {[mode.name for mode in Mode]}
              program:
                description: >-
                    Optional name of the program this dataset belongs to.
                type: string
                default: AOSSEQUENCE
              reason:
                description: Optional reason for taking the data.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              note:
                description: A descriptive note about the image being taken.
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
        self.n_sequences = config.n_sequences

        self.mode = getattr(Mode, config.mode)

        # Set program, reason and note
        self.program = config.program
        self.reason = config.reason
        self.note = config.note

    def set_metadata(self, metadata: salobj.type_hints.BaseMsgType) -> None:
        """Sets script metadata.

        Parameters
        ----------
        metadata : `salobj.type_hints.BaseMsgType`
            Script metadata topic. The information is set on the topic
            directly.
        """
        # Estimated duration is maximum number of iterations multiplied by
        # 3 or 2 multiplied by the time it takes to take an image
        # plus estimation on reading out the images (10s)
        number_of_images = 3 if self.mode == Mode.TRIPLET else 2

        metadata.duration = (
            self.n_sequences
            * number_of_images
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
                self.domain,
                log=self.log,
                tcs_ready_to_take_data=self.mtcs.ready_to_take_data,
            )
            await self.camera.start_task
        else:
            self.log.debug("Camera already defined, skipping.")

        if self.ocps is None:
            self.log.debug("Create OCPS remote.")

            self.ocps = salobj.Remote(self.domain, "OCPS", 101)

            await self.ocps.start_task

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

    async def take_aos_sequence(self) -> None:
        """Take out-of-focus sequence images."""
        supplemented_group_id = self.next_supplemented_group_id()

        if (
            self.mode == Mode.TRIPLET
            or self.mode == Mode.INTRA
            or self.mode == Mode.PAIR
        ):
            self.log.debug("Moving to intra-focal position")

            # Move the hexapod to the target z position
            z_offset = -self.dz - self.current_z_position
            await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
            self.current_z_position = -self.dz

            self.log.info("Taking in-focus image")
            self.camera.rem.ccoods.evt_imageInOODS.flush()
            intra_visit_id = await self.camera.take_cwfs(
                exptime=self.exposure_time,
                n=1,
                group_id=supplemented_group_id,
                filter=self.filter,
                reason="INTRA" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                note=self.note,
            )

        if (
            self.mode == Mode.TRIPLET
            or self.mode == Mode.EXTRA
            or self.mode == Mode.PAIR
        ):
            self.log.debug("Moving to extra-focal position")

            # Move the hexapod to the target z position
            z_offset = self.dz - self.current_z_position
            await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
            self.current_z_position = self.dz

            self.log.info("Taking extra-focal image")

            self.camera.rem.ccoods.evt_imageInOODS.flush()
            extra_visit_id = await self.camera.take_cwfs(
                exptime=self.exposure_time,
                n=1,
                group_id=supplemented_group_id,
                filter=self.filter,
                reason="EXTRA" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                note=self.note,
            )

        if self.mode == Mode.TRIPLET or self.mode == Mode.PAIR:
            self.log.debug("Waiting for images to be ingested in OODS.")
            extra_image_ingested = False
            while not extra_image_ingested:
                try:
                    image_in_oods = await self.camera.rem.ccoods.evt_imageInOODS.next(
                        flush=False, timeout=self.exposure_time
                    )
                    try:
                        image_name_split = image_in_oods.obsid.split("_")
                        image_index = int(
                            f"{image_name_split[-2]}{image_name_split[-1][1:]}"
                        )
                        extra_image_ingested = image_index == extra_visit_id[0]
                    except Exception:
                        self.log.exception(
                            "Failed to parse image name into index for {image_in_oods.obsid}."
                        )

                    self.log.info(
                        f"Image {image_in_oods.obsid} {image_in_oods.raft} {image_in_oods.sensor} ingested."
                    )

                except asyncio.TimeoutError:
                    self.log.warning(
                        "Timeout waiting for images to ingest. Continuing."
                    )
                    break
            self.log.info("Send processing request to RA OCPS.")
            config = {
                "LSSTComCam-FROM-OCS_DONUTPAIR": f"{intra_visit_id[0]},{extra_visit_id[0]}"
            }
            ocps_execute_task = asyncio.create_task(
                self.ocps.cmd_execute.set_start(
                    config=json.dumps(config),
                    timeout=self.camera.fast_timeout,
                )
            )

        self.log.debug("Moving to in-focus position")

        # Move the hexapod to the target z position
        z_offset = -self.current_z_position
        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
        self.current_z_position = 0

        if self.mode != Mode.PAIR:
            self.log.info("Taking in-focus image")
            self.camera.rem.ccoods.evt_imageInOODS.flush()
            await self.camera.take_acq(
                exptime=self.exposure_time,
                n=1,
                group_id=self.group_id,
                filter=self.filter,
                reason="INFOCUS" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                note=self.note,
            )

        if self.mode == Mode.TRIPLET:
            try:
                await ocps_execute_task
            except Exception:
                self.log.exception("Executing OCPS task failed. Ignoring.")

    async def run_block(self) -> None:
        """Execute script operations."""
        await self.assert_feasibility()

        for i in range(self.n_sequences):
            self.log.info(f"Starting aos sequence {i+1} of {self.n_sequences}")
            await self.checkpoint(f"out-of-focus sequence {i+1} of {self.n_sequences}")

            await self.take_aos_sequence()
