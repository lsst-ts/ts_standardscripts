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

import shlex
import random
import astropy
import asyncio
import logging
import unittest

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel.detector_characterization import ATGetStdFlatDataset

random.seed(47)  # for set_random_lsst_dds_partition_prefix

index_gen = salobj.index_generator()

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
            await asyncio.sleep(one_exp_time)

            self.end_readout_tasks.append(asyncio.create_task(self.end_readout(data)))

            if "bias" in parsed_data["imageType"].lower():
                self.n_bias += 1
            elif "dark" in parsed_data["imageType"].lower():
                self.n_dark += 1
            elif "flat" in parsed_data["imageType"].lower():
                self.n_flat += 1

        await self.end_readout_tasks[-1]

    async def end_readout(self):

        await asyncio.sleep(self.script.read_out_time)

        date_id = astropy.time.Time.now().tai.isot.split("T")[0].replace("-", "")
        image_name = f"test_latiss_{date_id}_{next(index_gen)}"

        self.at_cam.evt_endReadout.set_put(imageName=image_name)

        self.at_headerservice.evt_largeFileObjectAvailable.put()

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
            config = await self.configure_script(filter=1, grating=3, linear_stage=10)

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
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = (
            scripts_dir
            / "auxtel"
            / "detector_characterization"
            / "get_std_flat_dataset.py"
        )
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
