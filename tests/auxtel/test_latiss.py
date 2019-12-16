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

import unittest
import asynctest
import asyncio

from lsst.ts import salobj
from lsst.ts.standardscripts.auxtel.latiss import LATISS
from lsst.ts.standardscripts.auxtel.mock import LATISSMock


class Harness:
    def __init__(self):
        salobj.test_utils.set_random_lsst_dds_domain()

        self.latiss_remote = LATISS(salobj.Domain())
        self.latiss_mock = LATISSMock()

    async def __aenter__(self):
        await asyncio.gather(self.latiss_remote.start_task,
                             self.latiss_mock.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.latiss_mock.close(),
                             self.latiss_remote.close())


class TestLATISS(asynctest.TestCase):

    async def test_take_bias(self):
        async with Harness() as harness:
            nbias = 10
            await harness.latiss_remote.take_bias(nbias=nbias)
            self.assertEqual(harness.latiss_mock.nimages, nbias)
            self.assertEqual(len(harness.latiss_mock.exptime_list), nbias)
            for i in range(nbias):
                self.assertEqual(harness.latiss_mock.exptime_list[i], 0.)
            self.assertIsNone(harness.latiss_mock.latiss_linear_stage)
            self.assertIsNone(harness.latiss_mock.latiss_grating)
            self.assertIsNone(harness.latiss_mock.latiss_filter)

    async def test_take_darks(self):
        async with Harness() as harness:
            ndarks = 10
            exptime = 5.
            await harness.latiss_remote.take_darks(ndarks=ndarks,
                                                   exptime=exptime)
            self.assertEqual(harness.latiss_mock.nimages, ndarks)
            self.assertEqual(len(harness.latiss_mock.exptime_list), ndarks)
            for i in range(ndarks):
                self.assertEqual(harness.latiss_mock.exptime_list[i], exptime)
            self.assertIsNone(harness.latiss_mock.latiss_linear_stage)
            self.assertIsNone(harness.latiss_mock.latiss_grating)
            self.assertIsNone(harness.latiss_mock.latiss_filter)

    async def test_take_flats(self):
        async with Harness() as harness:
            nflats = 10
            exptime = 5.
            filter_id = 1
            grating_id = 1
            linear_stage = 100.

            await harness.latiss_remote.take_flats(nflats=nflats,
                                                   exptime=exptime,
                                                   filter=filter_id,
                                                   grating=grating_id,
                                                   linear_stage=linear_stage)
            self.assertEqual(harness.latiss_mock.nimages, nflats)
            self.assertEqual(len(harness.latiss_mock.exptime_list), nflats)
            for i in range(nflats):
                self.assertEqual(harness.latiss_mock.exptime_list[i], exptime)
            self.assertEqual(harness.latiss_mock.latiss_filter, filter_id)
            self.assertEqual(harness.latiss_mock.latiss_grating, grating_id)
            self.assertEqual(harness.latiss_mock.latiss_linear_stage, linear_stage)


if __name__ == '__main__':
    unittest.main()
