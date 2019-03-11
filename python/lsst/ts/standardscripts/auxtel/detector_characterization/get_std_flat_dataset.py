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
    """Implement script to get sensor characterization data.

    The definition is spelled out in https://jira.lsstcorp.org/browse/CAP-203
    and https://jira.lsstcorp.org/browse/CAP-206.

    Basically, this script will:

    1 - Take a set `n_dark` (default=10) dark images (shutter closed) with
        `t_dark` (default=400s) exposure time
    2 - Take a set of `n_bias` (default=10) bias
    3 - Flat field data:
        - Take a set of pairs of flat fields at a set of approximately
        logarithmically spaced intensity
        levels starting at 500 DN and increasing by a factor of 2 (i.e. 500,
        1000, 2000, ...).
        The exact levels are not important, but they must be well known; both
        the flux level and shutter time must be well measured (if shutter is
        opened before/closed after the lamp
        is turned on then the shutter time need not be well measured).
        - Take a set of `nb` biases after the entire flat sequence is complete

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index):

        super().__init__(index=index,
                         descr="Take Flat field sensor characterization data.",
                         remotes_dict=dict(atcam=salobj.Remote(SALPY_ATCamera,
                                                               include=["takeImages",
                                                                        "endReadout"]),
                                           atspec=salobj.Remote(SALPY_ATSpectrograph,
                                                                include=["changeFilter",
                                                                         "changeDisperser",
                                                                         "moveLinearStage"])))

        self.cmd_timeout = 30.
        self.end_readout_timeout = 120.

        self.read_out_time = None
        self.n_dark = None
        self.t_dark = None
        self.n_bias = None
        self.n_flat = None
        self.flat_base_exptime = None
        self.flat_dn_range = None
        self.filter = None
        self.grating = None
        self.linear_stage = None

        # FIXME: Get this parameter from the camera configuration once late
        # joiner is working
        # on the open network.
        self.maximum_exp_time = 401.  # Maximum exposure time in seconds.

    async def configure(self,
                        n_dark=10,
                        t_dark=400.,
                        n_bias=10,
                        n_flat=2,
                        flat_base_exptime=0.5,
                        flat_dn_range=(1., 2., 4., 8., 16., 32., 64., 128.),
                        filter_id=None,
                        grating_id=None,
                        linear_stage=None,
                        read_out_time=2.):
        """Configure script.

        Parameters
        ----------
        n_dark : `int` (optional)
            Number of dark images to be taken.
        t_dark : `float` (optional)
            Exposure time for the dark images in seconds.
        n_bias : `int` (optional)
            Number of bias images to be taken.
        n_flat : `int` (optional)
            Number of flat field images to take for each exposure time.
        flat_base_exptime : `float` (optional)
            The exposure time for the first flat field image set (in seconds).
        flat_dn_range : `list(float)` (optional)
            List of values that multiply the `flat_base_exptime`. For instance,
            if you want to take two sets of flat with exposure times
            `flat_base_exptime, 2*flat_base_exptime, 4*flat_dn_range`,
            `flat_dn_range = [1., 2., 4.]`.
        filter_id : `int` (optional)
            Id of the filter to use in the ATSpectrograph. If `None` (default)
            will ignore the setup step.
        grating_id : `int` (optional)
            Id of the grating to use in the ATSpectrograph. If `None`
            (default) will ignore the setup step.
        linear_stage : `float` (optional)
            Position of the linear stage in the ATSpectrograph. If `None`
            (default) will ignore the
            setup step.
        read_out_time :`float` (optional)
            The read out time of the camera, in seconds. Used to estimate
            script duration.

        """

        if int(n_dark) <= 0:
            raise RuntimeError(f"Number of dark frames must be larger than 0, got {n_dark}")
        self.n_dark = int(n_dark)

        if not (0. < float(t_dark) <= self.maximum_exp_time):
            raise RuntimeError(f"Dark exptime must be in the range "
                               f"(0.,{self.maximum_exp_time}], got {t_dark}")
        self.t_dark = float(t_dark)

        if int(n_bias) <= 0:
            raise RuntimeError(f"Number of bias frames must be larger than 0, got {n_bias}")
        self.n_bias = int(n_bias)

        if int(n_flat) <= 0:
            raise RuntimeError(f"Number of flat field frames must be larger than 0, got {n_flat}")
        self.n_flat = int(n_flat)

        if float(flat_base_exptime) < 0.:
            raise RuntimeError(f"Base flat field exposure time must be larger than 0., "
                               f"got {flat_base_exptime}.")
        self.flat_base_exptime = float(flat_base_exptime)

        self.flat_dn_range = np.array(flat_dn_range, dtype=float)

        if np.any(self.flat_dn_range <= 0.):
            n_bad = len(np.where(self.flat_dn_range <= 0.)[0])
            raise RuntimeError(f"'flat_dn_range' must be larger than zero. "
                               f"Got {n_bad} bad values.")

        larger_flat_exptime = np.max(self.flat_dn_range)*self.flat_base_exptime
        if larger_flat_exptime > self.maximum_exp_time:
            raise RuntimeError(f"Flat field maximum exposure time {larger_flat_exptime}s "
                               f"above maximum allowed {self.maximum_exp_time}s.")

        self.filter = filter_id

        self.grating = grating_id

        self.linear_stage = linear_stage

        if float(read_out_time) > 0.:
            self.read_out_time = float(read_out_time)
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
            await self.atspec.cmd_changeFilter.start(timeout=self.cmd_timeout)

        if self.grating is not None:
            await self.checkpoint(f"Configuring ATSpec grating; {self.grating}")
            self.atspec.cmd_changeDisperser.set(disperser=self.grating)
            await self.atspec.cmd_changeDisperser.start(timeout=self.cmd_timeout)

        if self.linear_stage is not None:
            await self.checkpoint(f"Configuring ATSpec linear stage; {self.linear_stage}")
            self.atspec.cmd_moveLinearStage.set(distanceFromHome=self.linear_stage)
            await self.atspec.cmd_moveLinearStage.start(timeout=self.cmd_timeout)

        await self.take_dark_sequence()

        await self.take_bias_sequence()

        await self.take_flat_sequence()

        await self.take_bias_sequence()

        await self.checkpoint("done")

    async def take_dark_sequence(self):
        """Take the intended sequence of darks.
        """
        self.log.info(f"Taking {self.n_dark} dark images...")

        for i in range(self.n_dark):
            await self.take_image(exp_time=self.t_dark,
                                  shutter=False,
                                  image_seq_name=f"dark_{i+1:04d}_{self.n_dark:04d}")

    async def take_bias_sequence(self):
        """Take the intended sequence of bias.
        """
        self.log.info(f"Taking {self.n_bias} bias images...")

        for i in range(self.n_bias):
            await self.take_image(exp_time=0.,
                                  shutter=False,
                                  image_seq_name=f"bias_{i+1:04d}_{self.n_bias:04d}")

    async def take_flat_sequence(self):
        """Take the intended sequence of flats.
        """
        self.log.info("Taking flat-field sequence...")

        for i in range(len(self.flat_dn_range)):
            for j in range(self.n_flat):
                await self.take_image(exp_time=self.flat_base_exptime * self.flat_dn_range[i],
                                      shutter=True,
                                      image_seq_name=f"flat_{i+1:04d}_"
                                                     f"{len(self.flat_dn_range):04d}_"
                                                     f"{j+1:04d}_"
                                                     f"{self.n_flat:04d}")

    async def take_image(self, exp_time, shutter, image_seq_name):
        """Encapsulates the take image routine.

        This basically consists of configuring and sending a takeImages
        command to the camera and waiting for a endReadout event.

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
        # FIXME: Current version of ATCamera software is not set up to take
        # images with numImages > 1, so this is fixed at 1 for now and we
        # loop through any set of images we want to take. (2019/03/11)
        self.atcam.cmd_takeImages.set(numImages=1,
                                      expTime=exp_time,
                                      shutter=shutter,
                                      imageSequenceName=str(image_seq_name))

        timeout = self.read_out_time + self.cmd_timeout + self.end_readout_timeout

        end_readout_coro = self.atcam.evt_endReadout.next(flush=True,
                                                          timeout=timeout)

        await self.checkpoint(f"Take image {image_seq_name}")

        await self.atcam.cmd_takeImages.start(timeout=timeout+exp_time)
        await end_readout_coro

    def set_metadata(self, metadata):
        dark_time = self.n_dark * (self.read_out_time + self.t_dark)
        # Note, bias is taken twice, once at the beginning then at the end of
        # the sequence.
        bias_time = 2. * self.n_bias * self.read_out_time
        flat_time = np.sum(self.n_flat * self.flat_dn_range * (self.read_out_time +
                                                               self.flat_base_exptime))
        metadata.duration = dark_time + bias_time + flat_time
