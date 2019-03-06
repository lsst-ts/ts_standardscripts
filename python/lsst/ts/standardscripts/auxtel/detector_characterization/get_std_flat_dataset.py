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

__all__ = ["ATGetStdFlatDataset"]

import numpy as np

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATCamera
import SALPY_ATSpectrograph


class ATGetStdFlatDataset(scriptqueue.BaseScript):
    """Implement script to get sensor characterization data. The definition is spelled out in
    https://jira.lsstcorp.org/browse/CAP-203 and https://jira.lsstcorp.org/browse/CAP-206.

    Basically, this script will:

    1 - Take a set `nd` (default=10) dark images (shutter closed) with `td` (default=400s) exposure time
    2 - Take a set of `nb` (default=10) bias
    3 - Flat field data:
        - Take a set of pairs of flat fields at a set of approximately logarithmically spaced intensity
        levels starting at 500 DN and increasing by a factor of 2 (i.e. 500, 1000, 2000, ...).
        The exact levels are not important, but they must be well known; both the flux level and
        shutter time must be well measured (if shutter is opened before/closed after the lamp
        is turned on then the shutter time need not be well measured).
        - Take a set of `nb` biases after the entire flat sequence is complete

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index,
                 descr="Take Flat field sensor characterization data."):

        super().__init__(index=index,
                         descr=descr,
                         remotes_dict=dict(atcam=salobj.Remote(SALPY_ATCamera,
                                                               include=["takeImages",
                                                                        "endReadout"]),
                                           atspec=salobj.Remote(SALPY_ATSpectrograph,
                                                                include=["changeFilter",
                                                                         "changeDisperser",
                                                                         "moveLinearStage"])))

        # Had to increase this timeout to accommodate some issue with the camera.
        self.cmd_timeout = 120.
        self.read_out_time = 2.
        self.n_dark = 10
        self.t_dark = 400.
        self.n_bias = 10
        self.n_flat = 2
        self.flat_base_exptime = 0.5
        self.flat_dn_range = np.array([1., 2., 4., 8., 16., 32., 64., 128.])
        self.filter = None
        self.grating = None
        self.linear_stage = None

        # FIXME: Get this parameter from the camera configuration once late joiner is working
        # on the open network.
        self.maximum_exp_time = 401.  # Maximum exposure time in seconds.

    async def configure(self,
                        n_dark=10,
                        t_dark=400.,
                        n_bias=10,
                        n_flat=2,
                        flat_base_exptime=10.,
                        flat_dn_range=None,
                        filter_id=None,
                        grating_id=None,
                        linear_stage=None,
                        read_out_time=2.):
        """Configure script.

        Parameters
        ----------
        n_dark : `int`
            Number of dark images to be taken (default=10).
        t_dark : `float`
            Exposure time for the dark images in seconds (default=400s).
        n_bias : `int`
            Number of bias images to be taken (default=10).
        n_flat : `int`
            Number of flat field images to take for each exposure time.
        flat_base_exptime : `float`
            The exposure time for the first flat field image set (in seconds).
        flat_dn_range : `list(float)`
            List of values that multiply the `flat_base_exptime`. For instance, if you want to take
            two sets of flat with exposure times `flat_base_exptime, 2*flat_base_exptime, 4*flat_dn_range`,
            `flat_dn_range = [1., 2., 4.]`. Default is [1., 2., 4., 8., 16., 32., 64.].
        filter_id : `int`
            Id of the filter to use in the ATSpectrograph. If `None` (default) will ignore the setup step.
        grating_id : `int`
            Id of the grating to use in the ATSpectrograph. If `None` (default) will ignore the setup step.
        linear_stage : `float`
            Position of the linear stage in the ATSpectrograph. If `None` (default) will ignore the
            setup step.
        read_out_time :`float`
            The read out time of the camera, in seconds. Used to estimate script duration.

        """

        if n_dark > 0:
            self.n_dark = n_dark
        else:
            raise RuntimeError(f"Number of dark frames must be larger than 0, got {n_dark}")

        if 0. < t_dark <= self.maximum_exp_time:
            self.t_dark = t_dark
        else:
            raise RuntimeError(f"Dark exptime must be in the range "
                               f"(0.,{self.maximum_exp_time}], got {t_dark}")

        if n_bias > 0:
            self.n_bias = n_bias
        else:
            raise RuntimeError(f"Number of bias frames must be larger than 0, got {n_bias}")

        if n_flat > 0:
            self.n_flat = n_flat
        else:
            raise RuntimeError(f"Number of flat field frames must be larger than 0, got {n_flat}")

        if flat_base_exptime > 0.:
            self.flat_base_exptime = flat_base_exptime
        else:
            raise RuntimeError(f"Base flat field exposure time must be larger than 0., "
                               f"got {flat_base_exptime}")

        if flat_dn_range is not None:
            self.flat_dn_range = np.array(flat_dn_range, dtype=float)

        if np.any(self.flat_dn_range <= 0.):
            n_bad = len(np.where(self.flat_dn_range <= 0.)[0])
            raise RuntimeError(f"'flat_dn_range' must be larger than zero. "
                               f"Got {n_bad} bad values.")

        larger_flat_exptime = np.max(self.flat_dn_range)*self.flat_base_exptime
        if larger_flat_exptime > self.maximum_exp_time:
            raise RuntimeError(f"Flat field maximum exposure time {larger_flat_exptime}s "
                               f"above maximum allowed {self.maximum_exp_time}s.")

        if filter_id is not None:
            self.filter = filter_id

        if grating_id is not None:
            self.grating = grating_id

        if linear_stage is not None:
            self.linear_stage = linear_stage

        if read_out_time > 0.:
            self.read_out_time = read_out_time
        else:
            self.log.warning(f"Read out time must be larger than 0., got {read_out_time}. "
                             f"Using default value, {self.read_out_time}s.")

    async def run(self):
        """Run method.
        """

        await self.checkpoint("setup")

        if self.filter is not None:
            await self.checkpoint(f"Configuring ATSpec filter; {self.filter}")
            self.atspec.cmd_changeFilter.set(filter=self.filter)
            await self.self.atspec.cmd_changeFilter.start(timeout=self.cmd_timeout)

        if self.grating is not None:
            await self.checkpoint(f"Configuring ATSpec grating; {self.grating}")
            self.atspec.cmd_changeDisperser.set(disperser=self.grating)
            await self.atspec.cmd_changeDisperser.start(timeout=self.cmd_timeout)

        if self.linear_stage is not None:
            await self.checkpoint(f"Configuring ATSpec linear stage; {self.linear_stage}")
            self.atspec.cmd_moveLinearStage.set(distanceFromHome=self.linear_stage)
            await self.atspec.cmd_moveLinearStage.start()

        await self.take_dark_sequence()

        await self.take_bias_sequence()

        await self.take_flat_sequence()

        await self.take_bias_sequence()

        await self.checkpoint("done")

    async def take_dark_sequence(self):
        """A coroutine to take the intended sequence of darks.
        """
        self.log.debug("Taking dark sequence...")

        for i in range(self.n_dark):
            await self.take_image(exp_time=self.t_dark,
                                  shutter=False,
                                  image_seq_name=f"dark_{i+1:04d}_{self.n_dark:04d}")

    async def take_bias_sequence(self):
        """A coroutine to take the intended sequence of bias.
        """
        self.log.debug("Taking bias sequence...")

        for i in range(self.n_bias):
            await self.take_image(exp_time=0.,
                                  shutter=False,
                                  image_seq_name=f"bias_{i+1:04d}_{self.n_bias:04d}")

    async def take_flat_sequence(self):
        """A coroutine to take the intended sequence of flats.
        """
        self.log.debug("Taking flat sequence...")

        for i in range(len(self.flat_dn_range)):
            for j in range(self.n_flat):
                await self.take_image(exp_time=self.flat_base_exptime * self.flat_dn_range[i],
                                      shutter=True,
                                      image_seq_name=f"flat_{i+1:04d}_"
                                                     f"{len(self.flat_dn_range):04d}_"
                                                     f"{j+1:04d}_"
                                                     f"{self.n_flat:04d}")

    async def take_image(self, exp_time, shutter, image_seq_name):
        """Coroutine to take images.

        Parameters
        ----------
        exp_time : `float`
            The exposure time for the image, in seconds.
        shutter : `bool`
            Should activate the shutter? (False for bias and dark)
        image_seq_name : `str`
            A string to identify the image.

        Returns
        -------

        """
        self.atcam.cmd_takeImages.set(numImages=1,
                                      expTime=exp_time,
                                      shutter=shutter,
                                      imageSequenceName=str(image_seq_name))

        timeout = self.read_out_time + self.cmd_timeout

        end_readout_coro = self.atcam.evt_endReadout.next(flush=True,
                                                          timeout=timeout)

        await self.checkpoint(f"Take image {image_seq_name}")

        await self.atcam.cmd_takeImages.start(timeout=timeout+exp_time)
        await end_readout_coro

    def set_metadata(self, metadata):
        metadata.duration = self.n_dark * (
            self.read_out_time + self.t_dark) + 2. * self.n_bias * self.read_out_time + np.sum(
            self.n_flat * self.flat_dn_range * (self.read_out_time + self.flat_base_exptime))
