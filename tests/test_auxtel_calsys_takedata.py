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
import unittest

import numpy as np
import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.auxtel.standardscripts import CalSysTakeData, get_scripts_dir
from lsst.ts.idl.enums import ATMonochromator, Script
from numpy.testing import assert_array_almost_equal, assert_array_equal

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestATCalSysTakeData(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        """Make script and controllers and return a list of all made."""
        self.script = CalSysTakeData(index=index)

        # mock controllers that use callback functions defined below
        # to handle the expected commands
        self.electrometer = salobj.Controller(name="Electrometer", index=1)
        self.monochromator = salobj.Controller(name="ATMonochromator")
        self.fiberspec = salobj.Controller(name="FiberSpectrograph")

        # data that is set by the command callback functions
        # scan durations from Electrometer startScanDt command
        self.scan_durations = []
        # data from FiberSpectrograph captureSpectImage command
        self.image_data = []
        # wavelengths from ATMonochromator changeWavelength command
        self.wavelengths = []
        # slit width data from ATMonochromator changeSlitWidth command
        self.slit_data = []
        # grating types from ATMonochromator gratingType command
        self.grating_types = []

        # assign the command callback functions
        self.electrometer.cmd_startScanDt.callback = self.startScanDt

        self.fiberspec.cmd_expose.callback = self.captureSpectImage

        self.monochromator.cmd_changeWavelength.callback = self.changeWavelength
        self.monochromator.cmd_changeSlitWidth.callback = self.changeSlitWidth
        self.monochromator.cmd_selectGrating.callback = self.selectGrating

        return (self.script, self.electrometer, self.monochromator, self.fiberspec)

    async def startScanDt(self, data):
        """Callback for Electrometer startScanDt command."""
        self.scan_durations.append(data.scanDuration)
        await asyncio.sleep(1.0)
        await self.electrometer.evt_detailedState.write()
        await asyncio.sleep(data.scanDuration)

    async def captureSpectImage(self, data):
        """Callback for FiberSpectrograph captureSpectImage command."""
        self.image_data.append(data)
        await asyncio.sleep(data.duration)

    async def changeWavelength(self, data):
        """Callback for ATMonochromator changeWavelength command."""
        self.wavelengths.append(data.wavelength)

    async def changeSlitWidth(self, data):
        """Callback for ATMonochromator changeSlitWidth command."""
        self.slit_data.append(data)

    async def selectGrating(self, data):
        """Callback for ATMonochromator selectGrating command."""
        self.grating_types.append(data.gratingType)

    async def test_configure(self):
        argnames = (
            "wavelengths",
            "integration_times",
            "grating_types",
            "entrance_slit_widths",
            "exit_slit_widths",
            "image_types",
            "lamps",
            "spectrometer_delays",
        )

        async with self.make_script():
            # configure requires wavelengths and integration_times
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script()

        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(wavelengths=100)

        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(integration_times=100)

        async with self.make_script():
            # if configured with a scalar then every element has length 1
            await self.configure_script(wavelengths=100, integration_times=31)
            assert_array_equal(self.script.config.wavelengths, [100])
            assert_array_equal(self.script.config.integration_times, [31])
            for argname in argnames:
                arg = getattr(self.script.config, argname)
                assert isinstance(arg, np.ndarray)
                assert len(arg) == 1

        async with self.make_script():
            # if configured with an array then
            # every element has the same length
            await self.configure_script(wavelengths=[100, 200], integration_times=31)
            assert_array_equal(self.script.config.wavelengths, [100, 200])
            assert_array_equal(self.script.config.integration_times, [31, 31])
            for argname in argnames:
                arg = getattr(self.script.config, argname)
                assert isinstance(arg, np.ndarray)
                assert len(arg) == 2

        async with self.make_script():
            await self.configure_script(
                wavelengths=100, integration_times=31, grating_types=[1, 2]
            )
            assert_array_equal(self.script.config.wavelengths, [100, 100])
            assert_array_equal(self.script.config.integration_times, [31, 31])
            assert_array_equal(self.script.config.grating_types, [1, 2])
            for argname in argnames:
                arg = getattr(self.script.config, argname)
                assert isinstance(arg, np.ndarray)
                assert len(arg) == 2

    async def test_run(self):
        async with self.make_script():
            config = await self.configure_script(
                wavelengths=[100, 600],
                integration_times=[1.5, 1.9],
                grating_types=[1, 2],
                entrance_slit_widths=[2.1, 2.2],
                exit_slit_widths=[3.3, 3.4],
                image_types=["test1", "test2"],
                lamps=["lamps1", "lamps2"],
                spectrometer_delays=[1.03, 1.04],
            )
            nimages = len(self.script.config.wavelengths)
            assert nimages == 2
            assert self.script.state.state == Script.ScriptState.CONFIGURED

            await self.run_script()
            assert self.script.state.state == Script.ScriptState.DONE

            desired_scan_durations = [
                config.integration_times[i] + 2 * config.spectrometer_delays[i]
                for i in range(nimages)
            ]
            assert_array_almost_equal(self.scan_durations, desired_scan_durations)
            assert [imd.type for imd in self.image_data] == config.image_types
            assert_array_almost_equal(
                [imd.duration for imd in self.image_data], config.integration_times
            )
            assert [imd.source for imd in self.image_data] == config.lamps
            assert_array_almost_equal(self.wavelengths, config.wavelengths)
            assert_array_almost_equal(self.grating_types, config.grating_types)
            desired_slits = []
            desired_slit_widths = []
            for i in range(nimages):
                desired_slits.append(ATMonochromator.Slit.EXIT)
                desired_slits.append(ATMonochromator.Slit.ENTRY)
                desired_slit_widths.append(config.exit_slit_widths[i])
                desired_slit_widths.append(config.entrance_slit_widths[i])
            assert [sd.slit for sd in self.slit_data] == desired_slits
            assert_array_almost_equal(
                [sd.slitWidth for sd in self.slit_data], desired_slit_widths
            )
            assert self.grating_types == config.grating_types

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "calsys_takedata.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
