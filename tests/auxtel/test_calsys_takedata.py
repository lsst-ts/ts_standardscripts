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
import unittest

import asynctest
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import yaml

from lsst.ts.idl.enums import ATMonochromator, Script
from lsst.ts import salobj
from lsst.ts.standardscripts.auxtel import CalSysTakeData

np.random.seed(47)

index_gen = salobj.index_generator()

logging.basicConfig()


class Harness:
    def __init__(self):
        self.index = next(index_gen)

        self.test_index = next(index_gen)

        self.script = CalSysTakeData(index=self.index)

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

    async def startScanDt(self, data):
        """Callback for Electrometer startScanDt command."""
        self.scan_durations.append(data.scanDuration)
        await asyncio.sleep(1.)
        self.electrometer.evt_detailedState.put()
        await asyncio.sleep(data.scanDuration)

    async def captureSpectImage(self, data):
        """Callback for FiberSpectrograph captureSpectImage command.
        """
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

    async def __aenter__(self):
        await asyncio.gather(self.script.start_task,
                             self.electrometer.start_task,
                             self.monochromator.start_task,
                             self.fiberspec.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.script.close(),
                             self.electrometer.close(),
                             self.monochromator.close(),
                             self.fiberspec.close())


class TestATCalSysTakeData(asynctest.TestCase):
    def setUp(self):
        salobj.set_random_lsst_dds_domain()

    async def test_configure(self):
        index = next(index_gen)

        argnames = ("wavelengths", "integration_times", "grating_types",
                    "entrance_slit_widths", "exit_slit_widths",
                    "image_types", "lamps", "spectrometer_delays")

        async with CalSysTakeData(index=index) as script:
            async def run_configure(**kwargs):
                script.set_state(Script.ScriptState.UNCONFIGURED)
                config_data = script.cmd_configure.DataType()
                if kwargs:
                    config_data.config = yaml.safe_dump(kwargs)
                await script.do_configure(config_data)

            # configure requires wavelengths and integration_times
            with self.assertRaises(salobj.ExpectedError):
                await run_configure()
            with self.assertRaises(salobj.ExpectedError):
                await run_configure(wavelengths=100)
            with self.assertRaises(salobj.ExpectedError):
                await run_configure(integration_times=100)

            # if configured with a scalar then every element has length 1
            await run_configure(wavelengths=100, integration_times=31)
            assert_array_equal(script.config.wavelengths, np.array([100], dtype=float))
            assert_array_equal(script.config.integration_times, np.array([31], dtype=int))
            for argname in argnames:
                arg = getattr(script.config, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 1)

            # if configured with an array then
            # every element has the same length
            await run_configure(wavelengths=[100, 200], integration_times=31)
            assert_array_equal(script.config.wavelengths, np.array([100, 200], dtype=float))
            assert_array_equal(script.config.integration_times, np.array([31, 31], dtype=int))
            for argname in argnames:
                arg = getattr(script.config, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 2)

            await run_configure(wavelengths=100, integration_times=31, grating_types=[1, 2])
            assert_array_equal(script.config.wavelengths, np.array([100, 100], dtype=float))
            assert_array_equal(script.config.integration_times, np.array([31, 31], dtype=int))
            assert_array_equal(script.config.grating_types, np.array([1, 2], dtype=int))
            for argname in argnames:
                arg = getattr(script.config, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 2)

    async def test_run(self):
        async with Harness() as harness:
            wavelengths = [100, 600]
            integration_times = [1.5, 1.9]
            grating_types = [1, 2]
            entrance_slit_widths = [2.1, 2.2]
            exit_slit_widths = [3.3, 3.4]
            image_types = ["test1", "test2"]
            lamps = ["lamps1", "lamps2"]
            spectrometer_delays = [1.03, 1.04]

            config_kwargs = dict(
                wavelengths=wavelengths,
                integration_times=integration_times,
                grating_types=grating_types,
                entrance_slit_widths=entrance_slit_widths,
                exit_slit_widths=exit_slit_widths,
                image_types=image_types,
                lamps=lamps,
                spectrometer_delays=spectrometer_delays,
            )
            config_data = harness.script.cmd_configure.DataType()
            config_data.config = yaml.safe_dump(config_kwargs)
            print(f"config={config_data.config!r}")
            await harness.script.do_configure(data=config_data)
            nimages = len(harness.script.config.wavelengths)
            self.assertEqual(nimages, 2)
            self.assertEqual(harness.script.state.state, Script.ScriptState.CONFIGURED)

            await harness.script.do_run(data=None)
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, Script.ScriptState.DONE)

            desired_scan_durations = [integration_times[i] + 2*spectrometer_delays[i]
                                      for i in range(nimages)]
            assert_array_almost_equal(harness.scan_durations, desired_scan_durations)
            self.assertEqual([imd.type for imd in harness.image_data], image_types)
            assert_array_almost_equal([imd.duration
                                       for imd in harness.image_data], integration_times)
            self.assertEqual([imd.source for imd in harness.image_data], lamps)
            assert_array_almost_equal(harness.wavelengths, wavelengths)
            assert_array_almost_equal(harness.grating_types, grating_types)
            desired_slits = []
            desired_slit_widths = []
            for i in range(nimages):
                desired_slits.append(ATMonochromator.Slit.EXIT)
                desired_slits.append(ATMonochromator.Slit.ENTRY)
                desired_slit_widths.append(exit_slit_widths[i])
                desired_slit_widths.append(entrance_slit_widths[i])
            self.assertEqual([sd.slit for sd in harness.slit_data], desired_slits)
            assert_array_almost_equal([sd.slitWidth for sd in harness.slit_data], desired_slit_widths)
            self.assertEqual(harness.grating_types, grating_types)


if __name__ == '__main__':
    unittest.main()
