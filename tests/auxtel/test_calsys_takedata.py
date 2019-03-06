import logging
import pathlib
import sys
import unittest
import asyncio

import yaml
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_Electrometer
import SALPY_ATMonochromator
import SALPY_FiberSpectrograph

FrontEntrance = SALPY_ATMonochromator.ATMonochromator_shared_Slit_FrontEntrance
FrontExit = SALPY_ATMonochromator.ATMonochromator_shared_Slit_FrontExit

np.random.seed(47)

index_gen = salobj.index_generator()


def make_script(index):
    tests_dir = pathlib.Path(__file__).resolve().parent.parent.parent
    script_dir = tests_dir / "scripts" / "auxtel"
    orig_path = sys.path
    try:
        sys.path.append(str(script_dir))
        import calsys_takedata
        script = calsys_takedata.CalSysTakeData(index=index)
    finally:
        sys.path[:] = orig_path
    script.log.setLevel(logging.INFO)
    script.log.addHandler(logging.StreamHandler())
    return script


class Harness:
    def __init__(self):
        self.index = next(index_gen)

        self.test_index = next(index_gen)

        self.script = make_script(index=self.index)

        # mock controllers that use callback functions defined below
        # to handle the expected commands
        self.electrometer = salobj.Controller(SALPY_Electrometer, 1)
        self.monochromator = salobj.Controller(SALPY_ATMonochromator)
        self.fiberspec = salobj.Controller(SALPY_FiberSpectrograph)

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

        self.fiberspec.cmd_captureSpectImage.callback = self.captureSpectImage

        self.monochromator.cmd_changeWavelength.callback = self.changeWavelength
        self.monochromator.cmd_changeSlitWidth.callback = self.changeSlitWidth
        self.monochromator.cmd_selectGrating.callback = self.selectGrating

    async def startScanDt(self, id_data):
        """Callback for Electrometer startScanDt command."""
        self.scan_durations.append(id_data.data.scanDuration)
        await asyncio.sleep(1.)
        self.electrometer.evt_detailedState.put()
        await asyncio.sleep(id_data.data.scanDuration)

    async def captureSpectImage(self, id_data):
        """Callback for FiberSpectrograph captureSpectImage command.
        """
        data = self.fiberspec.cmd_captureSpectImage.DataType()
        for fieldname in ("imageType", "integrationTime", "lamp"):
            setattr(data, fieldname, getattr(id_data.data, fieldname))
        self.image_data.append(data)
        await asyncio.sleep(id_data.data.integrationTime)

    async def changeWavelength(self, id_data):
        """Callback for ATMonochromator changeWavelength command."""
        self.wavelengths.append(id_data.data.wavelength)

    async def changeSlitWidth(self, id_data):
        """Callback for ATMonochromator changeSlitWidth command."""
        data = self.monochromator.cmd_changeSlitWidth.DataType()
        for fieldname in ("slit", "slitWidth"):
            setattr(data, fieldname, getattr(id_data.data, fieldname))
        self.slit_data.append(data)

    async def selectGrating(self, id_data):
        """Callback for ATMonochromator selectGrating command."""
        self.grating_types.append(id_data.data.gratingType)


class TestATCalSysTakeData(unittest.TestCase):
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()

    def xtest_configure(self):
        index = next(index_gen)

        argnames = ("wavelengths", "integration_times", "grating_types",
                    "entrance_slit_widths", "exit_slit_widths",
                    "image_types", "lamps", "spectrometer_delays")

        async def doit():
            script = make_script(index=index)

            # configure requires wavelengths and integration_times
            with self.assertRaises(TypeError):
                await script.configure()
            with self.assertRaises(TypeError):
                await script.configure(wavelengths=100)
            with self.assertRaises(TypeError):
                await script.configure(integration_times=100)

            # if configured with a scalar then every element has length 1
            await script.configure(wavelengths=100, integration_times=31)
            assert_array_equal(script.wavelengths, np.array([100], dtype=float))
            assert_array_equal(script.integration_times, np.array([31], dtype=int))
            for argname in argnames:
                arg = getattr(script, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 1)

            # if configured with an array then every element has the same length
            await script.configure(wavelengths=[100, 200], integration_times=31)
            assert_array_equal(script.wavelengths, np.array([100, 200], dtype=float))
            assert_array_equal(script.integration_times, np.array([31, 31], dtype=int))
            for argname in argnames:
                arg = getattr(script, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 2)

            await script.configure(wavelengths=100, integration_times=31, grating_types=[1, 2])
            assert_array_equal(script.wavelengths, np.array([100, 100], dtype=float))
            assert_array_equal(script.integration_times, np.array([31, 31], dtype=int))
            assert_array_equal(script.grating_types, np.array([1, 2], dtype=int))
            for argname in argnames:
                arg = getattr(script, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 2)

            # mismatched array types cause trouble
            with self.assertRaises(ValueError):
                await script.configure(wavelengths=100, integration_times=31,
                                       grating_types=[1, 2], exit_slit_widths=[1, 2, 3])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run(self):
        async def doit():
            harness = Harness()
            wavelengths = [100, 600]
            integration_times = [5, 2]
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
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            nimages = len(harness.script.wavelengths)
            self.assertEqual(nimages, 2)
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.DONE)

            desired_scan_durations = [integration_times[i] + 2*spectrometer_delays[i] for i in range(nimages)]
            assert_array_almost_equal(harness.scan_durations, desired_scan_durations)
            self.assertEqual([imd.imageType for imd in harness.image_data], image_types)
            assert_array_almost_equal([imd.integrationTime for imd in harness.image_data], integration_times)
            self.assertEqual([imd.lamp for imd in harness.image_data], lamps)
            assert_array_almost_equal(harness.wavelengths, wavelengths)
            assert_array_almost_equal(harness.grating_types, grating_types)
            desired_slits = []
            desired_slit_widths = []
            for i in range(nimages):
                desired_slits.append(FrontExit)
                desired_slits.append(FrontEntrance)
                desired_slit_widths.append(exit_slit_widths[i])
                desired_slit_widths.append(entrance_slit_widths[i])
            self.assertEqual([sd.slit for sd in harness.slit_data], desired_slits)
            assert_array_almost_equal([sd.slitWidth for sd in harness.slit_data], desired_slit_widths)
            self.assertEqual(harness.grating_types, grating_types)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
