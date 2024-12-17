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

import asyncio
import logging
import random
import shlex
import unittest

import astropy
from lsst.ts import salobj, standardscripts, utils
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.detector_characterization import ATGetStdFlatDataset

random.seed(47)  # for set_random_lsst_dds_partition_prefix

index_gen = utils.index_generator()

logging.basicConfig(level=logging.DEBUG)


class TestATGetStdFlatDataset(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = ATGetStdFlatDataset(index=index)

        # Adds controller to Test
        self.at_cam = salobj.Controller(name="ATCamera")
        self.at_spec = salobj.Controller(name="ATSpectrograph")
        self.at_headerservice = salobj.Controller(name="ATHeaderService")

        self.n_bias = 0
        self.n_dark = 0
        self.n_flat = 0

        self.filter = None
        self.grating = None
        self.linear_stage = None

        self.shutter_time = 1.0

        self.end_readout_tasks = []

        return (self.script, self.at_cam, self.at_spec, self.at_headerservice)

    async def cmd_take_images_callback(self, data):
        # parse keyValueMap to grab imageType
        lexer = shlex.shlex(data.keyValueMap)
        lexer.whitespace_split = True
        lexer.whitespace = ","
        parsed_data = dict(pair.split(":", 1) for pair in lexer)

        for i in range(data.numImages):
            one_exp_time = data.expTime
            if data.shutter:
                one_exp_time += self.shutter_time
            date_id = astropy.time.Time.now().tai.isot.split("T")[0].replace("-", "")
            image_name = f"test_latiss_{date_id}_{next(index_gen)}"

            await self.at_cam.evt_startIntegration.set_write(imageName=image_name)

            await asyncio.sleep(one_exp_time)

            self.end_readout_tasks.append(
                asyncio.create_task(self.end_readout(image_name=image_name))
            )

            if "bias" in parsed_data["imageType"].lower():
                self.n_bias += 1
            elif "dark" in parsed_data["imageType"].lower():
                self.n_dark += 1
            elif "flat" in parsed_data["imageType"].lower():
                self.n_flat += 1

        # The end readout tasks are scheduled sequentially and they all do the
        # exact same thing (wait read_out_time seconds and publish some
        # events). There they should all end sequentially and the last one
        # should end last, so we only need wait for the last one to complete.
        await self.end_readout_tasks[-1]

    async def end_readout(self, image_name):
        await asyncio.sleep(self.script.read_out_time)

        await self.at_cam.evt_endReadout.set_write(imageName=image_name)

        await self.at_headerservice.evt_largeFileObjectAvailable.write()

    async def cmd_change_filter_callback(self, data):
        self.filter = data.filter

    async def cmd_change_grating_callback(self, data):
        self.grating = data.disperser

    async def cmd_move_linear_stage_callback(self, data):
        self.linear_stage = data.distanceFromHome

    async def test_script(self):
        async with self.make_script():
            self.at_cam.cmd_takeImages.callback = self.cmd_take_images_callback
            self.at_spec.cmd_changeFilter.callback = self.cmd_change_filter_callback
            self.at_spec.cmd_changeDisperser.callback = self.cmd_change_grating_callback
            self.at_spec.cmd_moveLinearStage.callback = (
                self.cmd_move_linear_stage_callback
            )

            # Make sure configure works with no data
            await self.configure_script()

            # Now configure the spectrograph
            config = await self.configure_script(
                filter=1,
                grating=3,
                linear_stage=10,
                flat_dn_range=[1, 2, 3],
                t_dark=1.0,
            )

            await self.run_script()

            assert self.n_bias == self.script.config.n_bias * 2
            assert self.n_dark == self.script.config.n_dark
            assert (
                self.n_flat
                == len(self.script.config.flat_dn_range) * self.script.config.n_flat
            )
            assert self.filter == config.filter
            assert self.grating == config.grating
            assert self.linear_stage == config.linear_stage

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = (
            scripts_dir / "detector_characterization" / "get_std_flat_dataset.py"
        )
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
