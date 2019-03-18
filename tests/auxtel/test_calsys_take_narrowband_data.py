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
import SALPY_ATSpectrograph
import SALPY_ATCamera

# Get enumerations of slits
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
        import calsys_take_narrowband_data  # WHY IS THIS HERE AND NOT ABOVE?
        script = calsys_take_narrowband_data.CalSysTakeNarrowbandData(index=index)
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
        self.atcamera = salobj.Controller(SALPY_ATCamera)
        self.atspectrograph = salobj.Controller(SALPY_ATSpectrograph)

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
        # linear stage position ATSpectrograph moveLinearStage command
        self.latiss_linear_stage_pos = []
        # linear filter position ATSpectrograph changeFilter command
        self.latiss_filter_pos = []
        # linear grating position ATSpectrograph changeGrating command
        self.latiss_grating_pos = []
        # data from ATCamera takeImages command
        self.take_images = []

        # assign the command callback functions
        self.electrometer.cmd_startScanDt.callback = self.startScanDt

        self.fiberspec.cmd_captureSpectImage.callback = self.captureSpectImage

        self.monochromator.cmd_changeWavelength.callback = self.changeWavelength
        self.monochromator.cmd_changeSlitWidth.callback = self.changeSlitWidth
        self.monochromator.cmd_selectGrating.callback = self.selectGrating

        self.atspectrograph.cmd_changeFilter.callback = self.changeFilter
        self.atspectrograph.cmd_changeDisperser.callback = self.changeDisperser
        self.atspectrograph.cmd_moveLinearStage.callback = self.moveLinearStage

        self.atcamera.cmd_takeImages.callback = self.takeImages

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

    async def moveLinearStage(self, id_data):
        """Callback for ATSpectrograph moveLinearStage command."""
        self.latiss_linear_stage_pos.append(id_data.data.distanceFromHome)

    async def changeFilter(self, id_data):
        """Callback for ATSpectrograph changeFilter command."""
        self.latiss_filter_pos.append(id_data.data.filter)

    async def changeDisperser(self, id_data):
        """Callback for ATSpectrograph changeDisperser command."""
        self.latiss_grating_pos.append(id_data.data.disperser)

    async def takeImages(self, id_data):
        """Callback for ATCamera changeDisperser command."""
        data = self.atcamera.cmd_takeImages.DataType()
        for fieldname in ("numImages", "expTime", "shutter", "imageSequenceName"):
            setattr(data, fieldname, getattr(id_data.data, fieldname))
        self.take_images.append(data)


class TestATCalSysTakeData(unittest.TestCase):
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()

    def xtest_configure(self):
        index = next(index_gen)

        argnames = ("wavelengths", "integration_times", "mono_grating_types",
                    "mono_entrance_slit_widths", "mono_exit_slit_widths",
                    "image_types", "lamps", "fiber_spectrometer_delays",
                    "latiss_filter", "latiss_grating", "latiss_stage_pos",
                    "nimages_per_wavelength", "shutter", "image_sequence_name")

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

            # if configured with an array then
            # every element has the same length
            await script.configure(wavelengths=[100, 200], integration_times=31)
            assert_array_equal(script.wavelengths, np.array([100, 200], dtype=float))
            assert_array_equal(script.integration_times, np.array([31, 31], dtype=int))
            for argname in argnames:
                arg = getattr(script, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 2)

            await script.configure(wavelengths=100, integration_times=31, mono_grating_types=[1, 2])
            assert_array_equal(script.wavelengths, np.array([100, 100], dtype=float))
            assert_array_equal(script.integration_times, np.array([31, 31], dtype=int))
            assert_array_equal(script.mono_grating_types, np.array([1, 2], dtype=int))
            for argname in argnames:
                arg = getattr(script, argname)
                self.assertIs(type(arg), np.ndarray)
                self.assertEqual(len(arg), 2)

            # mismatched array types cause trouble, this checks for them
            with self.assertRaises(ValueError):
                await script.configure(wavelengths=100, integration_times=31,
                                       mono_grating_types=[1, 2], exit_slit_widths=[1, 2, 3])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run(self):
        async def doit():
            # This is the configuration of the script you use to test it with.
            harness = Harness()
            wavelengths = [500, 600]
            integration_times = [5, 2]
            mono_grating_types = [1, 2]  # do physical tests on 1,1
            mono_entrance_slit_widths = [3.1, 3.2]
            mono_exit_slit_widths = [3.3, 3.4]
            image_types = ["test1", "test2"]
            lamps = ["lamps1", "lamps2"]
            fiber_spectrometer_delays = [1.03, 1.04]

            latiss_filter = [0, 1]
            latiss_grating = [1, 0]
            latiss_stage_pos = [65, 65]
            nimages_per_wavelength = [1, 1]
            shutter = [1, 1]
            image_sequence_name = ['narrowband_flat', 'narrowband_arc']

            config_kwargs = dict(
                wavelengths=wavelengths,
                integration_times=integration_times,
                mono_grating_types=mono_grating_types,
                mono_entrance_slit_widths=mono_entrance_slit_widths,
                mono_exit_slit_widths=mono_exit_slit_widths,
                image_types=image_types,
                lamps=lamps,
                fiber_spectrometer_delays=fiber_spectrometer_delays,
                latiss_filter=latiss_filter,
                latiss_grating=latiss_grating,
                latiss_stage_pos=latiss_stage_pos,
                shutter=shutter,
                nimages_per_wavelength=nimages_per_wavelength,
                image_sequence_name=image_sequence_name
            )
            config_data = harness.script.cmd_configure.DataType()
            config_data.config = yaml.safe_dump(config_kwargs)
            print(f"config={config_data.config!r}")
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            nimages = len(harness.script.wavelengths)
            # Test that it is configured to take 2 images
            self.assertEqual(nimages, 2)
            # ??Test that script configures??
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            # Check that script ran successfully
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.DONE)

            desired_scan_durations = [integration_times[i] + 2*fiber_spectrometer_delays[i]
                                      for i in range(nimages)]
            assert_array_almost_equal(harness.scan_durations, desired_scan_durations)
            self.assertEqual([imd.imageType for imd in harness.image_data], image_types)
            # Test that integration times are correct
            assert_array_almost_equal([imd.integrationTime for imd in harness.image_data], integration_times)
            self.assertEqual([imd.lamp for imd in harness.image_data], lamps)
            assert_array_almost_equal(harness.wavelengths, wavelengths)
            assert_array_almost_equal(harness.grating_types, mono_grating_types)  # Why almost?
            # Verify slits have proper slit widths
            desired_slits = []
            desired_slit_widths = []
            for i in range(nimages):
                desired_slits.append(FrontExit)
                desired_slits.append(FrontEntrance)
                desired_slit_widths.append(mono_exit_slit_widths[i])
                desired_slit_widths.append(mono_entrance_slit_widths[i])
            self.assertEqual([sd.slit for sd in harness.slit_data], desired_slits)
            assert_array_almost_equal([sd.slitWidth for sd in harness.slit_data], desired_slit_widths)
            self.assertEqual(harness.grating_types, mono_grating_types)
            # Verify ATSpectrograph has the proper setup
            self.assertEqual(harness.latiss_grating_pos, latiss_grating)
            self.assertEqual(harness.latiss_filter_pos, latiss_filter)
            self.assertEqual(harness.latiss_linear_stage_pos, latiss_stage_pos)

            # Verify ATCamera took proper images
            desired_exptime = []
            desired_shutter = []
            desired_numImages = []
            desired_imageSequenceName = []

            for i in range(nimages):
                desired_exptime.append(integration_times[i])
                desired_shutter.append(shutter[i])
                desired_numImages.append(1)  # hardcoded for now
                desired_imageSequenceName.append(image_sequence_name[i])

            self.assertAlmostEqual([imd.expTime for imd in harness.take_images], desired_exptime)
            self.assertEqual([imd.shutter for imd in harness.take_images], desired_shutter)
            self.assertEqual([imd.numImages for imd in harness.take_images], desired_numImages)
            self.assertEqual([imd.imageSequenceName for imd in harness.take_images],
                             desired_imageSequenceName)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
