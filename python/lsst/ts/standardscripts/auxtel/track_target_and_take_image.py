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

__all__ = ["TrackTargetAndTakeImage"]

import yaml
import asyncio

from ..base_track_target_and_take_image import BaseTrackTargetAndTakeImage
from ..utils import format_as_list

from lsst.ts.observatory.control.utils import RotType
from lsst.ts.observatory.control.auxtel import ATCS, ATCSUsages, LATISS, LATISSUsages


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

    async def track_target_and_setup_instrument(self):
        """Track target and setup instrument in parallel."""

        self.tracking_started = True

        await asyncio.gather(
            self.atcs.slew_icrs(
                ra=self.config.ra,
                dec=self.config.dec,
                rot=self.config.rot_sky,
                rot_type=RotType.Sky,
                target_name=self.config.name,
            ),
            self.latiss.setup_atspec(
                grating=self.grating[0], filter=self.band_filter[0]
            ),
        )

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

        for exptime, grating, band_filter in zip(
            self.config.exp_times, self.grating, self.band_filter
        ):
            await self.latiss.take_object(
                exptime=exptime,
                group_id=self.group_id,
                filter=band_filter,
                grating=grating,
                reason=self.config.reason,
                program=self.config.program,
            )

    async def stop_tracking(self):
        """Execute stop_tracking command on ATCS."""
        await self.atcs.stop_tracking()
