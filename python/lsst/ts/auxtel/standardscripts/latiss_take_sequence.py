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

__all__ = ["LatissTakeSequence"]

import asyncio
import collections

import astropy.units
import yaml
from astropy.coordinates import ICRS, Angle
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import ATCS, LATISS, ATCSUsages, LATISSUsages
from lsst.ts.standardscripts.utils import format_as_list
from lsst.ts.xml.enums.Script import (
    MetadataCoordSys,
    MetadataDome,
    MetadataRotSys,
    ScriptState,
)

STD_TIMEOUT = 20  # seconds


class LatissTakeSequence(salobj.BaseScript):
    """Perform a sequence of exposures for a given set of instrument
    configurations.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    An (optional) checkpoint is available to verify the calculated
    telescope offset after each iteration of the acquisition.

    **Details**

    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Perform a sequence of images with LATISS.",
        )

        latiss_usage = None if add_remotes else LATISSUsages.DryTest

        atcs_usage = None if add_remotes else ATCSUsages.DryTest

        self.atcs = ATCS(domain=self.domain, intended_usage=atcs_usage, log=self.log)
        self.latiss = LATISS(
            domain=self.domain,
            intended_usage=latiss_usage,
            log=self.log,
            tcs_ready_to_take_data=self.atcs.ready_to_take_data,
        )

        self.run_started = False

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_externalscripts/auxtel/latiss_take_sequence.yaml
            title: LatissAcquireAndTakeSequence v1
            description: Configuration for LatissAcquireAndTakeSequence Script.
            type: object
            properties:
              program:
                description: Name of the program this dataset belongs to (required).
                type: string

              reason:
                description: Reason for taking the data (required).
                type: string

              filter_sequence:
                description: Filters for exposure sequence. If a single value is specified then
                   the same filter is used for each exposure.
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: string
                  - type: string
                default: empty_1

              grating_sequence:
                description: Gratings for exposure sequence. If a single value is specified then
                   the same grating is used for each exposure.
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: string
                  - type: string
                default: empty_1

              exposure_time_sequence:
                description: Exposure times for exposure sequence (sec). Each exposure requires
                   a specified exposure time.
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      minimum: 0
                  - type: number
                    minimum: 0
                default: 2.

              do_check_ataos_corrections:
                description: Check that ATAOS corrections are enabled before taking sequence.
                type: boolean
                default: True

              ra:
                description: ICRS right ascension (hour). Note this is ONLY used for script queue metadata.
                anyOf:
                  - type: number
                    minimum: 0
                    maximum: 24
                  - type: string

              dec:
                description: ICRS declination (deg). Note this is ONLY used for script queue metadata.
                anyOf:
                  - type: number
                    minimum: -90
                    maximum: 90
                  - type: string

              rot_sky:
                description: >-
                  The position angle in the Sky. 0 deg means that North is pointing up
                  in the images. Note this is ONLY used for script queue metadata.
                type: number


            required: ["program", "reason"]
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        # make a list of tuples from the filter, exptime and grating lists
        _recurrences = (
            len(config.exposure_time_sequence)
            if isinstance(config.exposure_time_sequence, collections.abc.Iterable)
            else 1
        )

        self.visit_configs = [
            (f, e, g)
            for f, e, g in zip(
                format_as_list(config.filter_sequence, _recurrences),
                format_as_list(config.exposure_time_sequence, _recurrences),
                format_as_list(config.grating_sequence, _recurrences),
            )
        ]

        self.reason = config.reason

        self.program = config.program

        self.exposure_time_sequence = config.exposure_time_sequence

        self.do_check_ataos_corrections = config.do_check_ataos_corrections

        self.ra = getattr(config, "ra", None)

        self.dec = getattr(config, "dec", None)

        self.rot_sky = getattr(config, "rot_sky", None)

    def set_metadata(self, metadata):
        metadata.duration = 0
        filters_gratings, exptime_total = set(), 0
        for filt, exptime, grating in self.visit_configs:
            if "empty" in filt:
                filt = "empty"
            if "empty" in grating:
                grating = "empty"
            exptime_total += exptime
            filters_gratings.add(f"{filt}~{grating}")
            metadata.duration += 3  # time to reconfigure latiss
        metadata.duration += exptime_total
        metadata.filters = ",".join(filters_gratings)
        metadata.survey = self.program
        if isinstance(self.exposure_time_sequence, float):
            metadata.nimages = 1
        else:
            metadata.nimages = len(self.exposure_time_sequence)
        metadata.coordinateSystem = MetadataCoordSys.ICRS
        if (self.ra is not None) and (self.dec is not None):
            radec_icrs = ICRS(
                Angle(self.ra, unit=astropy.units.hourangle),
                Angle(self.dec, unit=astropy.units.deg),
            )
            metadata.position = [radec_icrs.ra.deg, radec_icrs.dec.deg]
        if self.rot_sky is not None:
            metadata.rotationSystem = MetadataRotSys.SKY
            metadata.cameraAngle = self.rot_sky
        metadata.dome = MetadataDome.OPEN
        metadata.instrument = "LATISS"

    async def take_sequence(self):
        """Take data while making sure ATCS is tracking."""

        # TODO (DM-38822): Call self.atcs.assert_tracking().
        tasks = [
            asyncio.create_task(self._take_sequence()),
            asyncio.create_task(self.atcs.check_tracking()),
        ]

        await self.atcs.process_as_completed(tasks)

    async def _take_sequence(self):
        """Take the sequence of images as defined in visit_configs."""

        nexp = len(self.visit_configs)

        for i, (filt, exptime, grating) in enumerate(self.visit_configs):
            await self.latiss.take_object(
                exptime=exptime,
                n=1,
                filter=filt,
                grating=grating,
                group_id=self.group_id,
                reason=self.reason,
                program=self.program,
            )

            self.log.info(
                f"Completed exposure {i + 1} of {nexp}. Exptime = {exptime:6.1f}s,"
                f" filter={filt}, grating={grating})"
            )

    async def assert_feasibility(self) -> None:
        """Verify that the telescope and camera are in a feasible state to
        execute the script.
        """

        await self.latiss.assert_all_enabled()
        await self.atcs.assert_all_enabled()

        if self.do_check_ataos_corrections:
            await self.atcs.assert_ataos_corrections_enabled()

    async def run(self):
        self.run_started = True

        await self.assert_feasibility()

        await self.take_sequence()

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING and self.run_started:
            try:
                await self.atcs.stop_tracking()
            except asyncio.TimeoutError:
                self.log.exception(
                    "Stop tracking command timed out during cleanup procedure."
                )
            except Exception:
                self.log.exception("Unexpected exception in stop_tracking.")
