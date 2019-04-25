#!/usr/bin/env python

import asyncio
import collections

import numpy as np

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATMonochromator
import SALPY_Electrometer
import SALPY_FiberSpectrograph

__all__ = ["CalSysTakeData"]


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


class CalSysTakeData(scriptqueue.BaseScript):
    """
    """

    def __init__(self, index):
        super().__init__(index=index,
                         descr="Configure and take data from the auxiliary telescope CalSystem.",
                         remotes_dict={'electrometer': salobj.Remote(SALPY_Electrometer, 1),
                                       'monochromator': salobj.Remote(SALPY_ATMonochromator),
                                       'fiber_spectrograph': salobj.Remote(SALPY_FiberSpectrograph)})
        self.cmd_timeout = 10
        self.change_grating_time = 60

    async def configure(self, wavelengths, integration_times,
                        grating_types=1,
                        entrance_slit_widths=2,
                        exit_slit_widths=4,
                        image_types="test",
                        lamps="lamps",
                        spectrometer_delays=1,
                        ):
        """Configure the script.

        Parameters
        ----------
        wavelengths : `float` or `list` [`float`]
            Wavelength for each image (nm).
        integration_times :  : `float` or `list` [`float`]
            Integration time for each image (sec).
        grating_types : `int` or `list` [`int`]
            Grating type for each image. The choices are:

            * 1: red
            * 2: blue
            * 3: mirror
        entrance_slit_widths : `float` or `list` [`float`]
            Width of the monochrometer entrance slit for each image (mm).
        exit_slit_widths : `float` or `list` [`float`]
            Width of the monochrometer exit slit for each image (mm).
        image_types : `str` or `list` [`str`]
            Type of each image.
        lamps : `str` or `list` [`str`]
            Name of lamp for each image.
        spectrometer_delays : `float` or `list` [`float`]
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
        for argname in ("wavelengths", "integration_times", "grating_types",
                        "entrance_slit_widths", "exit_slit_widths",
                        "image_types", "lamps", "spectrometer_delays"):
            value = kwargs[argname]
            if is_sequence(value):
                nelt = len(value)
                break

        self.wavelengths = as_array(wavelengths, dtype=float, nelt=nelt)
        self.integration_times = as_array(integration_times, dtype=float, nelt=nelt)
        self.grating_types = as_array(grating_types, dtype=int, nelt=nelt)
        self.entrance_slit_widths = as_array(entrance_slit_widths, dtype=float, nelt=nelt)
        self.exit_slit_widths = as_array(exit_slit_widths, dtype=float, nelt=nelt)
        self.image_types = as_array(image_types, dtype=str, nelt=nelt)
        self.lamps = as_array(lamps, dtype=str, nelt=nelt)
        self.spectrometer_delays = as_array(spectrometer_delays, dtype=float, nelt=nelt)

        self.log.info("Configure completed")

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        nimages = len(self.lamps)
        metadata.duration = self.change_grating_time*nimages + np.sum(self.integration_times)

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
                slitWidth=self.exit_slit_widths[i])
            await self.monochromator.cmd_changeSlitWidth.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_changeSlitWidth.set(
                slit=SALPY_ATMonochromator.ATMonochromator_shared_Slit_FrontEntrance,
                slitWidth=self.entrance_slit_widths[i])
            await self.monochromator.cmd_changeSlitWidth.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_selectGrating.set(gratingType=self.grating_types[i])
            await self.monochromator.cmd_selectGrating.start(
                timeout=self.cmd_timeout+self.change_grating_time)

            await self.checkpoint("expose")

            # The electrometer startScanDt command is not reported as done
            # until the scan is done, so start the scan and then start
            # taking the image data
            self.electrometer.cmd_startScanDt.set(
                scanDuration=self.integration_times[i] + self.spectrometer_delays[i]*2)
            coro1 = self.electrometer.cmd_startScanDt.start()
            coro2 = self.start_take_spectrum(i)
            await asyncio.gather(coro1, coro2)

    async def start_take_spectrum(self, index):
        """Wait for `self.spectrometer_delays` then take a spectral image.

        Parameters
        ----------
        index : int
            Index of image to take.

        Returns
        -------
        cmd_captureSpectImage.start : coro
        """
        await self.electrometer.evt_detailedState.next(flush=True, timeout=self.cmd_timeout)
        await asyncio.sleep(self.spectrometer_delays[index])

        timeout = self.integration_times[index] + self.cmd_timeout
        self.fiber_spectrograph.cmd_captureSpectImage.set(
            imageType=self.image_types[index],
            integrationTime=self.integration_times[index],
            lamp=self.lamps[index],
        )
        self.log.info(f"take a {self.integration_times[index]} second exposure")
        return await self.fiber_spectrograph.cmd_captureSpectImage.start(timeout=timeout)


if __name__ == "__main__":
    CalSysTakeData.main()
