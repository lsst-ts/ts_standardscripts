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

__all__ = ["CcwRotatorStressTest"]

import yaml
import asyncio

import numpy as np

import astropy.units as u
from astropy.coordinates import Angle

from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages

np.random.seed(14)


class CcwRotatorStressTest(salobj.BaseScript):
    """Perform stress test between Camera Cable Wrap (CCW) and Rotator.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * rotator_angle: before staring each sequence of random rotator angle.

    * cycle: before each cycle of + and -.

    * reset_rotator: after first test completes, before reseting the Rotator
        position.

    * delay: Before each "delay test".

    **Details**

    The test consists of:

    * Start by slewing/tracking a circumpolar target with the rotator angle set
      to be close to zero.
    * Pick a configurable number of random rotator positions inside the limit.
    * For each random rotator position P slew to +P, wait for the Rotator to
      arrive at the position, let Rotator track for 15s and slew to -P. Repeat
      this 5 times.
    * Once done, reset to track a target with rotator angle close to zero.
    * Send a demand to track a target at +80 degrees, but send a new target
      in the other direction while the rotator is still slewing. Repeat this
      test after a configurable series of time delay after slewing started.



    Warning:
    --------
    This script requires to slew the telescope. Make sure the system is ready
    to slew before running the script.

    """

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Perform stress test between Camera Cable Wrap (CCW) and Rotator.",
        )

        self.mtcs = MTCS(
            domain=self.domain, log=self.log, intended_usage=MTCSUsages.Slew
        )

        # How long to track for before each new slew (in seconds).
        self.track_time = 15.0

        # Configuration parameters.
        self.n_rot_pos = 5
        self.n_pos_repeat = 3
        self.time_delays = np.array([1.0, 2.0, 5.0, 10.0])

        # Ignore CSCs that are not part of the test. This will allow us to run
        # the test if these CSCs are not enabled or being used for something
        # else.
        self.mtcs.check.mtaos = False
        self.mtcs.check.mtm1m3 = False
        self.mtcs.check.mtm2 = False
        self.mtcs.check.hexapod_1 = False
        self.mtcs.check.hexapod_2 = False
        self.mtcs.check.dome = False
        self.mtcs.check.mtdometrajectory = False

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    @classmethod
    def get_schema(cls):
        schema = """
        $schema: http://json-schema.org/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_standardscripts/maintel/CcwRotatorStressTest.yaml
        title: CcwRotatorStressTest v1
        description: Configuration for CcwRotatorStressTest.
        type: object
        properties:
            n_rot_pos:
                description: Number of random rotator positions to select.
                type: integer
                default: 5
                minimum: 0
            n_pos_repeat:
                description: Number of times to repeat each random position.
                type: integer
                default: 3
                minimum: 1
            time_delays:
                description: List of delays to send new targets after slew (in seconds).
                type: array
                default: [1., 2., 5., 10.]
                items:
                    type: number
                    minimum: 1.
                    maximum: 30.
        additionalProperties: false
        """
        return yaml.safe_load(schema)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration.
        """
        self.n_rot_pos = int(config.n_rot_pos)
        self.n_pos_repeat = int(config.n_pos_repeat)
        self.time_delays = np.array(config.time_delays)

        self.log.info(
            f"n_rot_pos: {self.n_rot_pos} x {self.n_pos_repeat}, time delays: {self.time_delays}"
        )

    async def run(self):

        self.log.info("Slewing telescope and positioning rotator close to zero.")

        time_and_date = await self.mtcs.rem.mtptg.tel_timeAndDate.aget()
        ra = Angle(time_and_date.lst, unit=u.hourangle)
        dec = Angle(-80.0, unit=u.degree)
        await self.mtcs.slew_icrs(
            ra=ra, dec=dec, rot_sky=-180.0, stop_before_slew=False
        )

        self.log.info("Slew complete. Tracking for {self.track_time}s.")
        await asyncio.sleep(self.track_time)

        random_pos = np.random.random(self.n_rot_pos) * 80.0

        self.log.debug(
            f"Starting first test. Selected random rotator angles: {random_pos}"
        )

        for rotator_angle in random_pos:

            await self.checkpoint(f"rotator_angle: {rotator_angle}")

            self.log.debug(f"Testing rotator angle {rotator_angle}")

            for i in range(self.n_pos_repeat):

                await self.checkpoint(f"cycle {i+1} of {self.n_pos_repeat}")

                self.log.debug("Slewing to + position.")

                time_and_date = await self.mtcs.rem.mtptg.tel_timeAndDate.aget()
                ra = Angle(time_and_date.lst, unit=u.hourangle)
                self.mtcs.rem.rotator.evt_inPosition.flush()
                await self.mtcs.slew_icrs(
                    ra=ra,
                    dec=dec,
                    rot_sky=-180.0 - rotator_angle,
                    stop_before_slew=False,
                )

                self.log.debug(
                    f"Arrived at + position, tracking for {self.track_time}s"
                )
                await asyncio.sleep(self.track_time)

                self.log.debug("Slewing to - position.")

                time_and_date = await self.mtcs.rem.mtptg.tel_timeAndDate.aget()
                ra = Angle(time_and_date.lst, unit=u.hourangle)
                self.mtcs.rem.rotator.evt_inPosition.flush()
                await self.mtcs.slew_icrs(
                    ra=ra,
                    dec=dec,
                    rot_sky=-180.0 + rotator_angle,
                    stop_before_slew=False,
                )

                self.log.debug(
                    f"Arrived at - position, tracking for {self.track_time}s"
                )
                await asyncio.sleep(15.0)

        await self.checkpoint("reset_rotator")
        self.log.info("First test completed. Reseting rotator.")

        time_and_date = await self.mtcs.rem.mtptg.tel_timeAndDate.aget()
        ra = Angle(time_and_date.lst, unit=u.hourangle)
        await self.mtcs.slew_icrs(
            ra=ra, dec=dec, rot_sky=-180.0, stop_before_slew=False
        )

        self.log.debug(f"Arrived at - position, tracking for {self.track_time}s")
        await asyncio.sleep(self.track_time)

        self.log.debug(f"Starting second test. Time delays: {self.time_delays}")

        for delay in self.time_delays:

            await self.checkpoint(f"delay {delay}s.")
            self.log.debug(f"Test delay: {delay}s.")

            time_and_date = await self.mtcs.rem.mtptg.tel_timeAndDate.aget()
            ra = Angle(time_and_date.lst, unit=u.hourangle)
            try:
                await self.mtcs.slew_icrs(
                    ra=ra,
                    dec=dec,
                    rot_sky=-180.0 + 80.0,
                    stop_before_slew=False,
                    slew_timeout=delay,
                )
            except asyncio.TimeoutError:
                pass

            await self.mtcs.slew_icrs(
                ra=ra, dec=dec, rot_sky=-180.0, stop_before_slew=False
            )

            self.log.debug(f"Arrived at - position, tracking for {self.track_time}s")
            await asyncio.sleep(self.track_time)

        self.log.info("Test completed.")

        await self.self.mtcs.stop_tracking()
