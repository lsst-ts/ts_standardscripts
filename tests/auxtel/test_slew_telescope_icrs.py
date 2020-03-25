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
import numpy as np

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel import SlewTelescopeIcrs

random.seed(47)  # for set_random_lsst_dds_domain

logging.basicConfig()


class TestSlewTelescopeIcrs(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):
        self.script = SlewTelescopeIcrs(index=index)

        self.location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                                    lat=-30.244728*u.deg,
                                                    height=2663.0*u.m)

        # mock controller that uses callback functions defined below
        # to handle the expected commands
        self.atptg = salobj.Controller("ATPtg")
        self.atdome = salobj.Controller("ATDome")
        self.atmcs = salobj.Controller("ATMCS")

        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)
        self.atdome.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)
        self.atptg_target = None
        self.track = False

        # assign the command callback functions
        self.atptg.cmd_raDecTarget.callback = self.raDecTarget

        self.tel_pos_task = asyncio.ensure_future(self.fake_tel_pos_telemetry())
        self.dome_pos_task = asyncio.ensure_future(self.dome_tel_pos_telemetry())
        self.time_and_date_task = asyncio.ensure_future(self.post_time_and_date())

        return (self.script, self.atptg, self.atdome, self.atmcs)

    async def close(self):
        """Shut down background telemetry tasks."""
        self.tel_pos_task.cancel()
        self.dome_pos_task.cancel()
        self.time_and_date_task.cancel()

    async def post_time_and_date(self):
        """Write ATPtg timeAndDate telemetry.
        """
        while True:
            now = Time.now()
            self.atptg.tel_timeAndDate.set_put(
                tai=now.tai.mjd,
                utc=now.utc.value.hour + now.utc.value.minute / 60. + (
                    now.utc.value.second
                    + now.utc.value.microsecond / 1e3) / 60. / 60.,
                lst=Angle(now.sidereal_time('mean',
                                            self.location.lon)).to_string(sep=':'),
            )
            await asyncio.sleep(0.05)

    async def raDecTarget(self, data):
        """Callback for ATPtg raDecTarget command.
        """
        self.atdome.evt_azimuthCommandedState.put()
        await asyncio.sleep(0.5)
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=False, force_output=True)
        await asyncio.sleep(0.5)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=False, force_output=True)

        self.track = True

        self.atptg_target = data

        asyncio.ensure_future(self.fake_slew(5.0))

    async def fake_slew(self, wait_time):
        """Pretend to slew by sleeping for the specified time (sec),
        then outputting allAxesInPosition and azimuthInPosition events.
        """
        await asyncio.sleep(wait_time)
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=True, force_output=True)
        await asyncio.sleep(0.5)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=True, force_output=True)

    async def fake_tel_pos_telemetry(self):
        while True:
            self.atmcs.tel_mount_AzEl_Encoders.set_put(
                elevationCalculatedAngle=np.zeros(100),
                azimuthCalculatedAngle=np.zeros(100),
            )

            self.atmcs.tel_mount_Nasmyth_Encoders.put()

            if self.track:
                self.atmcs.evt_target.set_put(
                    elevation=0.0, azimuth=0.0, force_output=True
                )

            await asyncio.sleep(1.0)

    async def dome_tel_pos_telemetry(self):
        while True:
            self.atdome.tel_position.set_put(azimuthPosition=0.0)
            await asyncio.sleep(1.0)

    async def test_configure_errors(self):
        """Test error handling in the do_configure method.
        """
        async with self.make_script():
            config_data = self.script.cmd_configure.DataType()
            for bad_config in (
                "ra: 5",  # dec missing
                "dec: 45",  # ra missing
                "ra: -0.001\ndec: 45",  # ra too small
                "ra: 24.001\ndec: 45",  # ra too big
                'ra: "5"\ndec: 45',  # ra not a float
                "ra: 5\ndec: 90.0001",  # dec too big
                "ra: 5\ndec: -90.0001",  # dec too small
                'ra: 5\ndec: "45"',  # dec not a float
                'ra: 5\ndec: 45\nrot_pa="5"',  # rot_pa not a float
            ):
                with self.subTest(bad_config=bad_config):
                    config_data.config = bad_config
                    with self.assertRaises(salobj.ExpectedError):
                        await self.script.do_configure(config_data)

    async def test_configure_with_defaults(self):
        async with self.make_script():
            config = await self.configure_script(ra=5.1, dec=36.2)

            self.assertEqual(self.script.config.ra, config.ra)
            self.assertEqual(self.script.config.dec, config.dec)
            self.assertEqual(self.script.config.rot_pa, 0)
            self.assertEqual(self.script.config.target_name, "")

    async def test_configure_no_defaults(self):
        async with self.make_script():
            config = await self.configure_script(
                ra=5.1, dec=36.2, rot_pa=-92.0, target_name="a target"
            )

            self.assertEqual(self.script.config.ra, config.ra)
            self.assertEqual(self.script.config.dec, config.dec)
            self.assertEqual(self.script.config.rot_pa, config.rot_pa)
            self.assertEqual(self.script.config.target_name, config.target_name)

    async def test_run(self):
        async with self.make_script():
            config = await self.configure_script(
                ra=8.0, dec=-15.0, rot_pa=0.0, target_name="test target"
            )
            await self.run_script()

            self.assertEqual(self.atptg_target.ra, config.ra)
            self.assertEqual(self.atptg_target.declination, config.dec)
            self.assertEqual(self.atptg_target.targetName, config.target_name)

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "slew_telescope_icrs.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
