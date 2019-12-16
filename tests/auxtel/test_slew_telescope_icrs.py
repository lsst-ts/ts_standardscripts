# This file is part of ts_standardscripts
#
# Developed for the LSST Data Management System.
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

import asyncio
import logging
import random
import unittest

import asynctest
import yaml
import numpy as np
from astropy.time import Time

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.standardscripts.auxtel import SlewTelescopeIcrs

random.seed(47)

index_gen = salobj.index_generator()

logging.basicConfig()


class Harness:
    def __init__(self):

        salobj.test_utils.set_random_lsst_dds_domain()

        self.index = next(index_gen)

        self.test_index = next(index_gen)

        self.script = SlewTelescopeIcrs(index=self.index)

        # mock controller that uses callback functions defined below
        # to handle the expected commands
        self.atptg = salobj.Controller("ATPtg")
        self.atdome = salobj.Controller("ATDome")
        self.atmcs = salobj.Controller("ATMCS")

        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)
        self.atdome.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)
        self.atptg_target = None
        self.track = False
        self.run_telemetry_loop = True

        # assign the command callback functions
        self.atptg.cmd_raDecTarget.callback = self.raDecTarget

        self.tel_pos_task = asyncio.ensure_future(self.fake_tel_pos_telemetry())
        self.dome_pos_task = asyncio.ensure_future(self.dome_tel_pos_telemetry())
        self.time_and_date_task = asyncio.ensure_future(self.post_time_and_date())

    async def post_time_and_date(self):

        while self.run_telemetry_loop:
            await asyncio.sleep(1.)
            now = Time.now()
            now.format = "mjd"
            self.atptg.tel_timeAndDate.set_put(tai=now.value)

    async def raDecTarget(self, data):
        """Callback for ATPtg raDecTarget command.
        """
        await asyncio.sleep(0.5)
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=False,
                                                 force_output=True)
        await asyncio.sleep(0.5)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=False,
                                                  force_output=True)

        self.track = True

        self.atptg_target = data

        asyncio.ensure_future(self.fake_slew(5.))

    async def fake_slew(self, wait_time):

        await asyncio.sleep(wait_time)
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=True,
                                                 force_output=True)
        await asyncio.sleep(0.5)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=True,
                                                  force_output=True)

    async def fake_tel_pos_telemetry(self):
        while self.run_telemetry_loop:

            self.atmcs.tel_mount_AzEl_Encoders.set_put(
                elevationCalculatedAngle=np.zeros(100),
                azimuthCalculatedAngle=np.zeros(100),
            )

            if self.track:
                self.atmcs.evt_target.set_put(elevation=0.,
                                              azimuth=0.,
                                              force_output=True)

            await asyncio.sleep(1.)

    async def dome_tel_pos_telemetry(self):
        while self.run_telemetry_loop:
            self.atdome.tel_position.set_put(azimuthPosition=0.)
            await asyncio.sleep(1.)

    async def __aenter__(self):
        await asyncio.gather(self.script.start_task,
                             self.atptg.start_task,
                             self.atdome.start_task,
                             self.atmcs.start_task)
        return self

    async def __aexit__(self, *args):
        self.run_telemetry_loop = False

        await asyncio.gather(self.tel_pos_task,
                             self.dome_pos_task,
                             self.time_and_date_task)

        await asyncio.gather(self.script.close(),
                             self.atptg.close(),
                             self.atdome.close(),
                             self.atmcs.close())


class TestSlewTelescopeIcrs(asynctest.TestCase):
    def setUp(self):
        # arbitrary sample data for use by most tests
        self.ra = 8.
        self.dec = -15.
        self.rot_pa = 0.
        self.target_name = "test target"

    def make_config_data(self):
        """Make config data using the default ra, dec, etc.

        Returns
        -------
        config : `str`
            Yaml-encoded configuration data for the
            script's do_configure command.
        """
        config_kwargs = dict(
            ra=self.ra,
            dec=self.dec,
            rot_pa=self.rot_pa,
            target_name=self.target_name,
        )
        return yaml.safe_dump(config_kwargs)

    async def test_configure_errors(self):
        """Test error handling in the do_configure method.
        """
        async with Harness() as harness:
            config_data = harness.script.cmd_configure.DataType()
            for bad_config in (
                'ra: 5',  # dec missing
                'dec: 45',  # ra missing
                'ra: -0.001\ndec: 45',  # ra too small
                'ra: 24.001\ndec: 45',  # ra too big
                'ra: "5"\ndec: 45',  # ra not a float
                'ra: 5\ndec: 90.0001',  # dec too big
                'ra: 5\ndec: -90.0001',  # dec too small
                'ra: 5\ndec: "45"',  # dec not a float
                'ra: 5\ndec: 45\nrot_pa="5"',  # rot_pa not a float
            ):
                with self.subTest(bad_config=bad_config):
                    config_data.config = bad_config
                    with self.assertRaises(salobj.ExpectedError):
                        await harness.script.do_configure(config_data)

    async def test_configure_with_defaults(self):
        async with Harness() as harness:
            config_data = harness.script.cmd_configure.DataType()
            config_data.config = "ra: 5.1\ndec: 36.2"
            await harness.script.do_configure(config_data)
            self.assertEqual(harness.script.config.ra, 5.1)
            self.assertEqual(harness.script.config.dec, 36.2)
            self.assertEqual(harness.script.config.rot_pa, 0)
            self.assertEqual(harness.script.config.target_name, "")

    async def test_configure_no_defaults(self):
        async with Harness() as harness:
            config_data = harness.script.cmd_configure.DataType()
            config_data.config = "ra: 5.1\ndec: 36.2\nrot_pa: -9.2\ntarget_name: a target"
            await harness.script.do_configure(config_data)
            self.assertEqual(harness.script.config.ra, 5.1)
            self.assertEqual(harness.script.config.dec, 36.2)
            self.assertEqual(harness.script.config.rot_pa, -9.2)
            self.assertEqual(harness.script.config.target_name, "a target")

    async def test_run(self):
        async with Harness() as harness:
            config_data = harness.script.cmd_configure.DataType()
            config_data.config = self.make_config_data()
            await harness.script.do_configure(data=config_data)
            self.assertEqual(harness.script.state.state, ScriptState.CONFIGURED)

            await harness.script.do_run(data=None)
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, ScriptState.DONE)

            self.assertEqual(harness.atptg_target.ra, self.ra)
            self.assertEqual(harness.atptg_target.declination, self.dec)
            self.assertEqual(harness.atptg_target.targetName, self.target_name)


if __name__ == '__main__':
    unittest.main()
