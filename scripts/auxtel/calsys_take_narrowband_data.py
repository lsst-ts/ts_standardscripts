#!/usr/bin/env python

import asyncio
import collections

import numpy as np

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATMonochromator
import SALPY_Electrometer
import SALPY_FiberSpectrograph
import SALPY_ATCamera
import SALPY_ATSpectrograph

__all__ = ["CalSysTakeNarrowbandData"]


def is_sequence(value):
    """Return True if value is a sequence that is not a `str` or `bytes`.
    """
    if isinstance(value, str) or isinstance(value, bytes):
        return False
    return isinstance(value, collections.Sequence)


def as_array(value, dtype, nelt):
    """Return a scalar or sequence as a 1-d array of specified type and length.

    Parameters
    ----------
    value : ``any`` or `list` [``any``]
        Value to convert to a list
    dtype : `type`
        Type of data for output
    nelt : `int`
        Required number of elements

    Returns
    -------
    array : `numpy.ndarray`
        ``value`` as a 1-dimensional array with the specified type and length.

    Raises
    ------
    ValueError
        If ``value`` is a sequence of the wrong length
    TypeError
        If ``value`` (if a scalar) or any of its elements (if a sequence)
        cannot be cast to ``dtype``.
    """
    if is_sequence(value):
        if len(value) != nelt:
            raise ValueError(f"len={len(value)} != {nelt}")
        return np.array(value, dtype=dtype)
    return np.array([value]*nelt, dtype=dtype)


class CalSysTakeNarrowbandData(scriptqueue.BaseScript):
    """
    """

    def __init__(self, index):
        super().__init__(index=index,
                         descr="Configure and take LATISS data using the"
                               "auxiliary telescope CalSystem.",
                         remotes_dict={'electrometer': salobj.Remote(SALPY_Electrometer, 1),
                                       'monochromator': salobj.Remote(SALPY_ATMonochromator),
                                       'fiber_spectrograph': salobj.Remote(SALPY_FiberSpectrograph),
                                       'atcamera': salobj.Remote(SALPY_ATCamera),
                                       'atspectrograph': salobj.Remote(SALPY_ATSpectrograph)})
        self.cmd_timeout = 10
        self.change_grating_time = 60

    async def configure(self, wavelengths, integration_times,
                        mono_grating_types=1,
                        mono_entrance_slit_widths=2,
                        mono_exit_slit_widths=4,
                        image_types="test",
                        lamps="Kiloarc",
                        fiber_spectrometer_delays=1,
                        latiss_filter=0,
                        latiss_grating=0,
                        latiss_stage_pos=60,
                        nimages_per_wavelength=1,
                        shutter=1,
                        image_sequence_name="test"
                        ):
        """Configure the script.

        Parameters
        ----------
        wavelengths : `float` or `list` [`float`]
            Wavelength for each image (nm).
        integration_times :  : `float` or `list` [`float`]
            Integration time for each image (sec).
        mono_grating_types : `int` or `list` [`int`]
            Grating type for each image. The choices are:

            * 1: red
            * 2: blue
            * 3: mirror
        mono_entrance_slit_widths : `float` or `list` [`float`]
            Width of the monochrometer entrance slit for each image (mm).
        mono_exit_slit_widths : `float` or `list` [`float`]
            Width of the monochrometer exit slit for each image (mm).
        image_types : `str` or `list` [`str`]
            Type of each image.
        lamps : `str` or `list` [`str`]
            Name of lamp for each image.
        fiber_spectrometer_delays : `float` or `list` [`float`]
            Delay before taking each image (sec).

        Raises
        ------
        salobj.ExpectedError :
            If the lengths of all arguments that are sequences do not match.

        Notes
        -----
        Arguments can be scalars or sequences. All sequences must have the
        same length, which is the number of images taken. If no argument
        is a sequence then one image is taken.
        """
        self.log.info("Configure started")

        nelt = 1
        kwargs = locals()
        for argname in ("wavelengths", "integration_times", "mono_grating_types",
                        "mono_entrance_slit_widths", "mono_exit_slit_widths",
                        "image_types", "lamps", "fiber_spectrometer_delays",
                        "latiss_filter", "latiss_grating", "latiss_stage_pos",
                        "nimages_per_wavelength", "shutter", "image_sequence_name"):
            value = kwargs[argname]
            if is_sequence(value):
                nelt = len(value)
                break

        # Monochromator Setup
        self.wavelengths = as_array(wavelengths, dtype=float, nelt=nelt)
        self.integration_times = as_array(integration_times, dtype=float, nelt=nelt)
        self.mono_grating_types = as_array(mono_grating_types, dtype=int, nelt=nelt)
        self.mono_entrance_slit_widths = as_array(mono_entrance_slit_widths, dtype=float, nelt=nelt)
        self.mono_exit_slit_widths = as_array(mono_exit_slit_widths, dtype=float, nelt=nelt)
        self.image_types = as_array(image_types, dtype=str, nelt=nelt)
        self.lamps = as_array(lamps, dtype=str, nelt=nelt)
        #Fiber spectrograph
        self.fiber_spectrometer_delays = as_array(fiber_spectrometer_delays, dtype=float, nelt=nelt)
        #ATSpectrograph Setup
        self.latiss_filter = as_array(latiss_filter, dtype=int, nelt=nelt)
        self.latiss_grating = as_array(latiss_grating, dtype=int, nelt=nelt)
        self.latiss_stage_pos = as_array(latiss_stage_pos, dtype=int, nelt=nelt)
        #ATCamera
        self.image_sequence_name = as_array(image_sequence_name, dtype=str, nelt=nelt)
        self.shutter = as_array(shutter, dtype=int, nelt=nelt)
        self.nimages_per_wavelength = as_array(nimages_per_wavelength, dtype=int, nelt=nelt)
        self.log.info("Configure completed")
        # note that the ATCamera exposure time uses self.integration_times for this version

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        nimages = len(self.lamps)
        metadata.duration = self.change_grating_time*nimages + \
                            np.sum((self.integration_times+2)*self.nimages_per_wavelength)

    async def run(self):
        """Run script."""

        await self.checkpoint("start")

        nelt = len(self.wavelengths)
        for i in range(nelt):
            self.log.info(f"take image {i} of {nelt}")

            await self.checkpoint("setup")

            self.monochromator.cmd_changeWavelength.set(wavelength=self.wavelengths[i])
            await self.monochromator.cmd_changeWavelength.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_changeSlitWidth.set(
                slit=SALPY_ATMonochromator.ATMonochromator_shared_Slit_FrontExit,
                slitWidth=self.mono_exit_slit_widths[i])
            await self.monochromator.cmd_changeSlitWidth.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_changeSlitWidth.set(
                slit=SALPY_ATMonochromator.ATMonochromator_shared_Slit_FrontEntrance,
                slitWidth=self.mono_entrance_slit_widths[i])
            await self.monochromator.cmd_changeSlitWidth.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_selectGrating.set(gratingType=self.mono_grating_types[i])
            await self.monochromator.cmd_selectGrating.start(
                timeout=self.cmd_timeout+self.change_grating_time)

            # Setup ATSpectrograph
            self.atspectrograph.cmd_changeDisperser.set(disperser=self.latiss_grating[i])
            await self.atspectrograph.cmd_changeDisperser.start(timeout=self.cmd_timeout)

            self.atspectrograph.cmd_changeFilter.set(filter=self.latiss_filter[i])
            await self.atspectrograph.cmd_changeFilter.start(timeout=self.cmd_timeout)

            self.atspectrograph.cmd_moveLinearStage.set(distanceFromHome=self.latiss_stage_pos[i])
            await self.atspectrograph.cmd_moveLinearStage.start(timeout=self.cmd_timeout)

            # setup ATCamera
            # Because we take ancillary data at the same time as the image, we can only take
            # 1 image at a time, therefore numImages is hardcoded to be 1.
            self.atcamera.cmd_takeImages.set(shutter=self.shutter[i],
                                             numImages=1,
                                             expTime=self.integration_times[i],
                                             imageSequenceName=self.image_sequence_name[i])


            await self.checkpoint("expose")

            # The electrometer startScanDt command is not reported as done
            # until the scan is done, so start the scan and then start
            # taking the image data
            self.electrometer.cmd_startScanDt.set(
                scanDuration=self.integration_times[i] + self.fiber_spectrometer_delays[i]*2)
            coro1 = self.electrometer.cmd_startScanDt.start()
            coro2 = self.start_take_spectrum(i)
            coro3 = self.atcamera.cmd_takeImages.start(timeout=self.cmd_timeout)
            await asyncio.gather(coro1, coro2)

    async def start_take_spectrum(self, index):
        """Wait for `self.fiber_spectrometer_delays` then take a spectral image.

        Parameters
        ----------
        index : int
            Index of image to take.

        Returns
        -------
        cmd_captureSpectImage.start : coro
        """
        await self.electrometer.evt_detailedState.next(flush=True, timeout=self.cmd_timeout)
        await asyncio.sleep(self.fiber_spectrometer_delays[index])

        timeout = self.integration_times[index] + self.cmd_timeout
        self.fiber_spectrograph.cmd_captureSpectImage.set(
            imageType=self.image_types[index],
            integrationTime=self.integration_times[index],
            lamp=self.lamps[index],
        )
        self.log.info(f"take a {self.integration_times[index]} second exposure")
        return await self.fiber_spectrograph.cmd_captureSpectImage.start(timeout=timeout)


if __name__ == '__main__':
    CalSysTakeNarrowbandData.main()
