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

import logging
import random
import unittest
import asyncio

import yaml

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.standardscripts.auxtel import SlewTelescopeIcrs

random.seed(47)

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):
        self.index = next(index_gen)

        self.test_index = next(index_gen)

        self.script = SlewTelescopeIcrs(index=self.index)
        self.script.log.addHandler(logging.StreamHandler())

        # mock controller that uses callback functions defined below
        # to handle the expected commands
        self.atptg = salobj.Controller("ATPtg")
        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)
        self.atptg_target = None

        # assign the command callback functions
        self.atptg.cmd_raDecTarget.callback = self.raDecTarget

    async def raDecTarget(self, data):
        """Callback for ATPtg raDecTarget command.
        """
        self.atptg_target = data

    async def __aenter__(self):
        await self.script.start_task
        await self.atptg.start_task
        return self

    async def __aexit__(self, *args):
        await self.script.close()
        await self.atptg.close()


class TestSlewTelescopeIcrs(unittest.TestCase):
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()

        # arbitrary sample data for use by most tests
        self.ra = 8
        self.dec = 15
        self.rot_pa = 1
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

    def test_configure_errors(self):
        """Test error handling in the do_configure method.
        """
        async def doit():
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

        asyncio.get_event_loop().run_until_complete(doit())

    def test_configure_with_defaults(self):
        async def doit():
            async with Harness() as harness:
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = "ra: 5.1\ndec: 36.2"
                await harness.script.do_configure(config_data)
                self.assertEqual(harness.script.config.ra, 5.1)
                self.assertEqual(harness.script.config.dec, 36.2)
                self.assertEqual(harness.script.config.rot_pa, 0)
                self.assertEqual(harness.script.config.target_name, "")

        asyncio.get_event_loop().run_until_complete(doit())

    def test_configure_no_defaults(self):
        async def doit():
            async with Harness() as harness:
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = "ra: 5.1\ndec: 36.2\nrot_pa: -9.2\ntarget_name: a target"
                await harness.script.do_configure(config_data)
                self.assertEqual(harness.script.config.ra, 5.1)
                self.assertEqual(harness.script.config.dec, 36.2)
                self.assertEqual(harness.script.config.rot_pa, -9.2)
                self.assertEqual(harness.script.config.target_name, "a target")

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run(self):
        async def doit():
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
                self.assertEqual(harness.atptg_target.rotPA, self.rot_pa)
                self.assertEqual(harness.atptg_target.targetName, self.target_name)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
