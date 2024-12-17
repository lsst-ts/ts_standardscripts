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

__all__ = ["TrackTargetAndTakeImage"]

import asyncio

import yaml
from lsst.ts.observatory.control.auxtel import ATCS, LATISS, ATCSUsages, LATISSUsages
from lsst.ts.observatory.control.utils import RotType
from lsst.ts.standardscripts.base_track_target_and_take_image import (
    BaseTrackTargetAndTakeImage,
)
from lsst.ts.standardscripts.utils import format_as_list


class TrackTargetAndTakeImage(BaseTrackTargetAndTakeImage):
    """Track target and take image script.

    This script implements a simple visit consistig of slewing to a target,
    start tracking and take image.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    add_remotes : `bool` (optional)
        Create remotes to control components (default: `True`)? If False, the
        script will not work for normal operations. Useful for unit testing.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index=index, descr="Track target and take image with AuxTel.")

        atcs_usage, latiss_usage = (
            (ATCSUsages.Slew, LATISSUsages.TakeImageFull)
            if add_remotes
            else (ATCSUsages.DryTest, LATISSUsages.DryTest)
        )

        self.atcs = ATCS(self.domain, intended_usage=atcs_usage, log=self.log)
        self.latiss = LATISS(self.domain, intended_usage=latiss_usage, log=self.log)

        self.instrument_name = "LATISS"

    @property
    def tcs(self):
        return self.atcs

    @classmethod
    def get_schema(cls):
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/auxtel/track_target_and_take_image.py
title: TrackTargetAndTakeImage v1
description: Configuration for TrackTargetAndTakeImage with AuxTel.
type: object
properties:
  grating:
    description: Name of the grating for observation.
    anyOf:
      - type: array
        minItems: 1
        items:
          type: string
      - type: string
  filter_prefix:
    description: Prefix to add to filter name.
    type: string
    default: ""
  filter_suffix:
    description: Suffix to append to filter name.
    type: string
    default: ""
required:
  - grating
additionalProperties: false
        """

        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = cls.get_base_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        schema_dict["required"] += base_schema_dict["required"]

        return schema_dict

    def get_instrument_name(self):
        return self.instrument_name

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """
        await super().configure(config)

        self.grating = format_as_list(config.grating, len(config.exp_times))
        self.band_filter = format_as_list(config.band_filter, len(config.exp_times))

    async def load_playlist(self):
        """Load playlist."""
        await self.latiss.rem.atcamera.cmd_play.set_start(
            playlist=self.config.camera_playlist,
            repeat=True,
            timeout=self.latiss.fast_timeout,
        )

    async def track_target_and_setup_instrument(self):
        """Track target and setup instrument in parallel."""

        self.tracking_started = True

        setup_atspec_task = asyncio.create_task(
            self.latiss.setup_atspec(
                grating=self.grating[0],
                filter=f"{self.config.filter_prefix}{self.band_filter[0]}{self.config.filter_suffix}",
            )
        )

        await self.atcs.slew_icrs(
            ra=self.config.ra,
            dec=self.config.dec,
            rot=self.config.rot_sky,
            rot_type=RotType.Sky,
            target_name=self.config.name,
            az_wrap_strategy=self.config.az_wrap_strategy,
            time_on_target=self.get_estimated_time_on_target(),
        )

        await setup_atspec_task

        await self.checkpoint("done")

    async def take_data(self):
        """Take data while making sure ATCS is tracking."""

        tasks = [
            asyncio.create_task(self._take_data()),
            asyncio.create_task(self.atcs.check_tracking()),
        ]

        await self.atcs.process_as_completed(tasks)

    async def _take_data(self):
        """Take data."""

        if self.is_standard_visit():
            self.log.debug(
                f"Same instrument setup for all images. using n={len(self.config.exp_times)}."
            )
            # Note that we are not passing the filter and grating information
            # take_object, this is handled in track_target_and_setup_instrument
            # concurrently to slewing to the target. Since all exposures have
            # the same configuration, we don't need to set them here again.
            await self.latiss.take_object(
                exptime=self.config.exp_times[0],
                n_snaps=len(self.config.exp_times),
                group_id=self.group_id,
                reason=self.config.reason,
                program=self.config.program,
            )

        else:
            self.log.debug(
                "Different instrument setup for images. Taking one at a time."
            )

            for exptime, grating, band_filter in zip(
                self.config.exp_times, self.grating, self.band_filter
            ):
                await self.latiss.take_object(
                    exptime=exptime,
                    n=1,
                    group_id=self.group_id,
                    filter=f"{self.config.filter_prefix}{band_filter}{self.config.filter_suffix}",
                    grating=grating,
                    reason=self.config.reason,
                    program=self.config.program,
                )

    async def stop_tracking(self):
        """Execute stop_tracking command on ATCS."""
        await self.atcs.stop_tracking()

    def is_standard_visit(self) -> bool:
        """Determine if script configuration specify a standard visit or a
        set of observations with different configurations.

        A standard visit consists of a sequence of images with the
        same instrument configuration and exposure time.

        Returns
        -------
        bool
            True if instrument configuration and exposure time is the same for
            all exposures.
        """
        return all(
            [
                len(set(item)) == 1
                for item in (self.config.exp_times, self.grating, self.band_filter)
            ]
        )

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        await asyncio.gather(
            self.atcs.assert_all_enabled(),
            self.latiss.assert_all_enabled(),
        )

        await self.atcs.assert_ataos_corrections_enabled()
