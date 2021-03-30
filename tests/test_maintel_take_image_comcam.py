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

import random
import unittest

import asynctest

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.maintel import TakeImageComCam

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestTakeImageComCam(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):

        self.script = TakeImageComCam(index=index)

        return (self.script,)

    async def test_configure(self):

        async with self.make_script():

            exp_times = 1.1
            image_type = "OBJECT"
            await self.configure_script(exp_times=exp_times, image_type=image_type)
            self.assertEqual(self.script.config.exp_times, [exp_times])
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertIsNone(self.script.config.filter)

            exp_times = 1.1
            image_type = "OBJECT"
            nimages = 2
            filter = None
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
            )
            self.assertEqual(self.script.config.exp_times, [exp_times, exp_times])
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertEqual(self.script.config.filter, filter)

            exp_times = 1.1
            nimages = 2
            filter = "blue"
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
            )
            self.assertEqual(self.script.config.exp_times, [exp_times, exp_times])
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertEqual(self.script.config.filter, filter)

            exp_times = [0, 2, 0.5]
            filter = 2
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                filter=filter,
            )
            self.assertEqual(self.script.config.exp_times, exp_times)
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertEqual(self.script.config.filter, filter)

            exp_times = [0, 2, 0.5]
            nimages = len(exp_times) + 1
            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(
                    exp_times=exp_times, image_type=image_type, nimages=nimages
                )

    async def test_take_images(self):

        async with self.make_script():

            self.script.camera.take_imgtype = asynctest.CoroutineMock()

            nimages = 5

            await self.configure_script(
                nimages=nimages,
                exp_times=1.0,
                image_type="OBJECT",
                filter=1,
            )

            await self.run_script()

            self.assertEqual(nimages, self.script.camera.take_imgtype.await_count)

    async def test_executable(self):

        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_image_comcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
