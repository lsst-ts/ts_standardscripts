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

__all__ = ["OpenDropoutDoor"]

import asyncio

from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.atcs import ATCS

STD_TIMEOUT = 5


class OpenDropoutDoor(salobj.BaseScript):
    """
    A SAL script for opening the dropout door of the Auxiliary Telescope's
    dome based on current wind conditions as reported by the Environmental
    Sensor Suite 301 (ESS 301).

    This script checks wind conditions to ensure it's safe to operate the
    dropout door. It considers both the median wind speed and gustiness
    (maximum wind speed and standard deviation of the wind speed). If wind
    conditions are found to be unsafe, the script aborts the operation by
    raising a RuntimeError.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Checking wind speed": Marks the start of the wind speed check.
    - "Opening dropout door": Marks the start of the operation.

    **Warnings**

    - If the script cannot determine the wind speed due to a communication
      timeout, it logs a warning and proceeds cautiously. Ensure manual
      verification of safety under such circumstances.

    **Exceptions**

    - Raises RuntimeError if the wind conditions are deemed unsafe for
      operating the dropout door, describing the current wind conditions
      that led to the abort.



    """

    def __init__(self, index):
        super().__init__(index=index, descr="Open the ATDome dropout door.")

        self.atcs = None
        self.ess_remote = None

        # Wind speed limits
        self.median_threshold = 8.0
        self.max_threshold = 10.0
        self.std_dev_threshold = 3.0

    @classmethod
    def get_schema(cls):
        # This script does not require any configuration
        return None

    async def configure(self, config):
        if self.atcs is None:
            self.atcs = ATCS(domain=self.domain, log=self.log)
            await self.atcs.start_task

        if self.ess_remote is None:
            self.ess_remote = salobj.Remote(domain=self.domain, name="ESS", index=301)
            await self.ess_remote.start_task

    def set_metadata(self, metadata):
        metadata.duration = 120.0

    async def assert_wind_safe(
        self, median_threshold, max_threshold, std_dev_threshold
    ):
        """Asserts wind conditions are safe for operating the dropout door.

        This function uses median wind speed, maximum wind speed, and
        the standard deviation of wind speed to assess wind conditions.
        Conditions are considered unsafe if the median wind speed exceeds
        the median threshold or if the maximum wind speed exceeds the maximum
        threshold, especially when the standard deviation is above a specified
        limit, indicating gusty conditions.

        Parameters
        ----------
        median_threshold : float, optional
            The threshold for median wind speed (m/s), default is 8.0 m/s.
        max_threshold : float, optional
            The threshold for maximum wind speed (m/s), default is 10.0 m/s.
        std_dev_threshold : float, optional
            The threshold for the standard deviation of wind speed (m/s),
            default is 3.0 m/s.

        Raises
        ------
        RuntimeError
            If the wind conditions are unsafe to opeen the dropout door,
            detailing the current wind conditions that led to the decision.
        """
        try:
            await self.checkpoint("Checking wind speed.")
            air_flow = await self.ess_remote.tel_airFlow.next(
                flush=True,
                timeout=STD_TIMEOUT,
            )

            if air_flow.speedStdDev > std_dev_threshold:
                # Increase sensitivity to wind when variability is high
                median_threshold *= 0.8
                max_threshold *= 0.8

            assert (
                air_flow.speed < median_threshold and air_flow.maxSpeed < max_threshold
            ), (
                f"Unsafe wind conditions: Median speed {air_flow.speed} m/s, "
                f"Max speed {air_flow.maxSpeed} m/s, "
                f"Standard deviation {air_flow.speedStdDev} m/s."
            )

        except asyncio.TimeoutError:
            self.log.warning(
                "Cannot determine wind speed. Proceeding with caution. "
                "Ensure it is safe to open."
            )

    async def run(self):
        await self.checkpoint("Opening dropout door.")

        # Assert wind conditions are safe before proceeding
        await self.assert_wind_safe(
            median_threshold=self.median_threshold,
            max_threshold=self.max_threshold,
            std_dev_threshold=self.std_dev_threshold,
        )

        # Proceed with opening the door if safe
        await self.atcs.open_dropout_door()
        self.log.info("Dropout door opened.")
