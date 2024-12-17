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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import contextlib
import logging
import types
import unittest

import pytest
from lsst.ts import salobj
from lsst.ts.auxtel.standardscripts import LatissTakeSequence, get_scripts_dir
from lsst.ts.standardscripts import BaseScriptTestCase


class TestLatissTakeSequence(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.ataos_hexapod_correction_status = True
        self.ataos_m1_correction_status = True
        self.ataos_atspectrograph_correction_status = True
        return super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger(type(cls).__name__)

    async def basic_make_script(self, index):
        self.script = LatissTakeSequence(index=index, add_remotes=False)

        self.end_image_tasks = []

        # things to track
        self.nimages = 0
        self.date = None  # Used to fake dataId output from takeImages
        self.seq_num_start = None  # Used to fake proper dataId from takeImages

        self.log.debug("Finished initializing from basic_make_script")

        return [
            self.script,
        ]

    async def get_evt_correctionEnabled(self, timeout):
        return types.SimpleNamespace(
            hexapod=self.ataos_hexapod_correction_status,
            m1=self.ataos_m1_correction_status,
            atspectrograph=self.ataos_atspectrograph_correction_status,
        )

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.latiss.take_object = unittest.mock.AsyncMock()
        self.script.atcs.check_tracking = unittest.mock.AsyncMock()
        self.script.atcs.stop_tracking = unittest.mock.AsyncMock()
        self.script.atcs.disable_ataos_corrections = unittest.mock.AsyncMock()

        self.script.atcs.rem.ataos = unittest.mock.AsyncMock()
        self.script.atcs.rem.ataos.configure_mock(
            **{
                "evt_correctionEnabled.aget.side_effect": self.get_evt_correctionEnabled,
            }
        )
        yield

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "latiss_take_sequence.py"
        self.log.debug(f"Checking for script in {script_path}")
        await self.check_executable(script_path)

    async def test_configure_with_minimum_parameters(self):
        async with self.make_script(), self.setup_mocks():
            # Try configure with minimum set of parameters declared
            # Note that all are scalars and should be converted to arrays
            grating_sequence = "test_disp1"
            filter_sequence = "test_filt1"
            reason = "test"
            program = "test_program"
            exposure_time_sequence = 1.0
            await self.configure_script(
                program=program,
                reason=reason,
                grating_sequence=grating_sequence,
                filter_sequence=filter_sequence,
                exposure_time_sequence=exposure_time_sequence,
            )

            for i, v in enumerate(self.script.visit_configs):
                assert self.script.visit_configs[i] == (
                    filter_sequence,
                    exposure_time_sequence,
                    grating_sequence,
                )

    async def test_configure_with_no_ataos_corrections(self):
        async with self.make_script(), self.setup_mocks():
            # Try to configure without checking tracking and ataos corrections
            grating_sequence = "test_disp1"
            filter_sequence = "test_filt1"
            reason = "test"
            program = "test_program"
            exposure_time_sequence = 1.0
            do_check_ataos_corrections = False
            await self.configure_script(
                program=program,
                reason=reason,
                grating_sequence=grating_sequence,
                filter_sequence=filter_sequence,
                exposure_time_sequence=exposure_time_sequence,
                do_check_ataos_corrections=do_check_ataos_corrections,
            )

            for i, v in enumerate(self.script.visit_configs):
                assert self.script.visit_configs[i] == (
                    filter_sequence,
                    exposure_time_sequence,
                    grating_sequence,
                )

    async def test_bad_configuration(self):
        async with self.make_script(), self.setup_mocks():
            # Try configure mis-matched array sizes. This should fail
            grating_sequence = ["test_disp1", "test_disp2"]
            exposure_time_sequence = [1.0, 2.0, 3.0]
            program = "test_program"
            reason = "test"
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(
                    program=program,
                    reason=reason,
                    grating_sequence=grating_sequence,
                    exposure_time_sequence=exposure_time_sequence,
                )

    async def test_take_sequence(self):
        async with self.make_script(), self.setup_mocks():
            self.log.info("Starting test_take_sequence")
            # Date for file to be produced
            self.date = "20200315"
            # sequence number start
            self.seq_num_start = 120
            grating_sequence = ["test_disp1", "test_disp2"]
            filter_sequence = ["test_filt1", "test_filt2"]
            reason = "test"
            program = "test_program"
            exposure_time_sequence = [0.3, 0.8]
            do_check_ataos_corrections = True
            await self.configure_script(
                program=program,
                reason=reason,
                grating_sequence=grating_sequence,
                filter_sequence=filter_sequence,
                exposure_time_sequence=exposure_time_sequence,
                do_check_ataos_corrections=do_check_ataos_corrections,
            )

            await self.run_script()

            # assert take_object was called correct number of times
            assert self.script.latiss.take_object.call_count == len(
                self.script.visit_configs
            )
