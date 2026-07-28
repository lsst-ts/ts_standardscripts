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

__all__ = ["WaitForSunElevation"]

import asyncio

import astropy.units as u
import yaml
from astroplan import Observer
from astropy.coordinates import EarthLocation
from lsst.ts import salobj, utils
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages

# Rubin Observatory site coordinates, matching BaseTCS.location.
RUBIN_LOCATION = EarthLocation.from_geodetic(
    lon=-70.747698 * u.deg, lat=-30.244728 * u.deg, height=2663.0 * u.m
)


class WaitForSunElevation(salobj.BaseScript):
    """Wait until the sun reaches a target elevation.

    This script polls the current solar elevation and blocks the script
    queue until the sun descends (or ascends) to the specified elevation.
    The primary use-case is to pause the queue just before nautical
    twilight ends (-12 deg) or astronomical twilight ends (-18 deg) so
    that subsequent scripts start automatically at the right time.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Details**

    Solar elevation is obtained via ``MTCS.get_sun_azel``, which uses the
    Rubin Observatory site coordinates defined in ``BaseTCS``.  The script
    sleeps for ``poll_interval`` seconds between checks and emits a
    checkpoint on every iteration so operators can monitor progress.
    """

    def __init__(self, index: int) -> None:
        super().__init__(
            index=index,
            descr="Wait until the sun reaches a target elevation.",
        )

        self.mtcs = MTCS(
            domain=self.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.log,
        )

        self._observer = Observer(
            location=RUBIN_LOCATION,
            name="Rubin",
            timezone="Chile/Continental",
        )

    @classmethod
    def get_schema(cls) -> dict:
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/wait_for_sun_elevation.yaml
            title: WaitForSunElevation v1
            description: Configuration for WaitForSunElevation script.
            type: object
            properties:
                target_elevation:
                    description: >-
                        Solar elevation (degrees) at which the script
                        completes. The script exits once the sun is at or
                        below this value. Negative values correspond to
                        positions below the horizon.
                    type: number
                    default: -10.0
                poll_interval:
                    description: >-
                        Time in seconds to sleep between solar elevation
                        checks.
                    type: number
                    minimum: 1
                    default: 5.0
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config: object) -> None:
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration with fields ``target_elevation`` and
            ``poll_interval``.
        """
        self.target_elevation = config.target_elevation
        self.poll_interval = config.poll_interval

    def set_metadata(self, metadata: object) -> None:
        metadata.duration = self.estimate_duration()

    def estimate_duration(self) -> float:
        """Estimate the remaining time until the sun reaches target elevation.

        Returns
        -------
        `float`
            Estimated duration in seconds.  Returns 0 if the sun is already
            at or below the target elevation.
        """
        now_tai = utils.astropy_time_from_tai_unix(utils.current_tai())

        _, sun_el = self.get_sun_azel()
        if sun_el <= self.target_elevation:
            return 0.0

        target_time = self._observer.sun_set_time(
            now_tai,
            which="next",
            horizon=self.target_elevation * u.deg,
        )
        return float(target_time.unix_tai - utils.current_tai())

    def get_sun_azel(self) -> tuple[float, float]:
        """Get the current sun azimuth and elevation at the Rubin site.

        Returns
        -------
        `tuple`[`float`, `float`]
            Sun azimuth and elevation in degrees.
        """
        return self.mtcs.get_sun_azel()

    async def run(self) -> None:
        _, sun_el = self.get_sun_azel()

        if sun_el <= self.target_elevation:
            self.log.info(
                f"Sun already at {sun_el:.2f} deg, at or below target "
                f"{self.target_elevation:.2f} deg. Nothing to do."
            )
            return

        self.log.info(
            f"Waiting for sun to reach {self.target_elevation:.2f} deg. "
            f"Current elevation: {sun_el:.2f} deg."
        )

        while sun_el > self.target_elevation:
            await self.checkpoint(
                f"Sun @ {sun_el:.2f} deg, waiting for {self.target_elevation:.2f} deg."
            )
            self.log.debug(f"Sleeping {self.poll_interval} s...")
            await asyncio.sleep(self.poll_interval)
            _, sun_el = self.get_sun_azel()

        self.log.info(
            f"Sun reached {sun_el:.2f} deg (target {self.target_elevation:.2f} deg). Done."
        )
