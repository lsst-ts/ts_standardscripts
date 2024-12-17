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

__all__ = ["PrepareForVent"]

import asyncio
import dataclasses

import yaml
from astroplan import Observer
from lsst.ts import salobj, utils
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages


@dataclasses.dataclass
class VentConstraints:
    sun_elevation_max = 90.0
    sun_elevation_min = 5.0

    def __repr__(self) -> str:
        return (
            "VentConstraints:: \n\n"
            f"Sun elevation between {self.sun_elevation_max} and {self.sun_elevation_min} degrees.\n"
        )


class PrepareForVent(salobj.BaseScript):
    """Run prepare for vent on ATCS.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index, remotes=True):
        super().__init__(index=index, descr="Prepare for vent.")

        self.track_sun_sleep_time = 60.0

        self.vent_constraints = VentConstraints()

        self.atcs = ATCS(
            domain=self.domain,
            log=self.log,
            intended_usage=None if remotes else ATCSUsages.DryTest,
        )

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/prepare_for/vent.yaml
            title: PrepareForVent v1
            description: Configuration for Prepare for vent.
            type: object
            properties:
                end_at_sun_elevation:
                    description: >-
                        Stop venting when sun reaches this altitude.
                    type: number
                    default: 0.0
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = self.estimate_duration()

    async def run(self):
        sun_az, sun_el = self.get_sun_azel()

        self.assert_vent_feasibility(sun_az, sun_el)

        await self.checkpoint("Preparing...")

        await self.prepare_for_vent()

        self.log.info(f"Venting until sun reaches {self.config.end_at_sun_elevation}.")

        while sun_el > self.config.end_at_sun_elevation:
            await self.checkpoint(
                f"Sun @ {sun_el:.2f} deg [limit={self.config.end_at_sun_elevation}]. "
            )
            self.log.debug(f"Waiting {self.track_sun_sleep_time}...")
            await asyncio.sleep(self.track_sun_sleep_time)

            (
                tel_vent_azimuth,
                dome_vent_azimuth,
            ) = self.atcs.get_telescope_and_dome_vent_azimuth()

            self.log.debug(
                f"Repositioning the telescope and dome: {tel_vent_azimuth=}, {dome_vent_azimuth}."
            )

            await self.reposition_telescope_and_dome(
                tel_vent_azimuth, dome_vent_azimuth
            )
            _, sun_el = self.get_sun_azel()

    async def reposition_telescope_and_dome(self, tel_vent_azimuth, dome_vent_azimuth):
        try:
            await self.atcs.point_azel(
                target_name="Vent Position",
                az=tel_vent_azimuth,
                el=self.atcs.tel_vent_el,
                rot_tel=self.atcs.tel_park_rot,
                wait_dome=False,
            )
            await self.atcs.stop_tracking()

            await self.atcs.slew_dome_to(dome_vent_azimuth)
        except Exception:
            self.log.exception(
                "Error repositioning the telescope and/or done. Continuing..."
            )

    async def prepare_for_vent(self):
        await self.atcs.prepare_for_vent(partially_open_dome=True)

    def get_sun_azel(self):
        """Get sun azel from ATCS.

        Returns
        -------
        `tuple`[`float`, `float`]
            Current azimuth and elevation of the sun.
        """
        return self.atcs.get_sun_azel()

    def assert_vent_feasibility(self, sun_az, sun_el):
        """Check that it is ok to vent, raise an exception if not.

        Parameters
        ----------
        sun_az : `float`
            Sun azimuth in degrees.
        sun_el : `float`
            Sun elevation, in degrees.

        Raises
        ------
        RuntimeError
            If not in the vent band.
        """
        if (
            sun_el > self.vent_constraints.sun_elevation_max
            or sun_el < self.vent_constraints.sun_elevation_min
        ):
            raise RuntimeError(
                f"Vent constraints not met. Sun currently @ {sun_az=:.2f},{sun_el=:.2f}. "
                f"Constraints are {self.vent_constraints!r}."
            )

    def estimate_duration(self):
        """Estimate the script duration.

        Returns
        -------
        `float`
            Estimated duration (in seconds).
        """

        observer = Observer(
            location=self.atcs.location, name="Rubin", timezone="Chile/Continental"
        )

        time_sunset = observer.sun_set_time(
            utils.astropy_time_from_tai_unix(utils.current_tai()), which="next"
        )

        return time_sunset.unix_tai - utils.current_tai()
