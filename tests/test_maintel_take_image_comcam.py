# This file is part of ts_standardscripts
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

import random
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.maintel.standardscripts import TakeImageComCam
from lsst.ts.xml.enums import Script

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestTakeImageComCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeImageComCam(index=index)

        return (self.script,)

    async def test_configure_with_metadata_and_slew_time_sim(self):
        async with self.make_script():
            exp_times = 1.1
            image_type = "OBJECT"
            visit_metadata = dict(ra=10.0, dec=-90.0, rot_sky=5.0)
            slew_time = 10

            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                visit_metadata=visit_metadata,
                slew_time=slew_time,
                sim=True,
            )
            assert self.script.config.exp_times == [exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter is None
            assert self.script.config.visit_metadata == visit_metadata
            assert self.script.config.slew_time == slew_time
            assert self.script.get_instrument_name() == "LSSTComCamSim"

    async def test_configure_no_filter(self):
        async with self.make_script():
            exp_times = 1.1
            image_type = "OBJECT"
            nimages = 2
            filter = None
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
            )
            assert self.script.config.exp_times == [exp_times, exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter

    async def test_configure_filter_as_str(self):
        async with self.make_script():
            exp_times = 1.1
            nimages = 2
            filter = "blue"
            image_type = "OBJECT"
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
            )
            assert self.script.config.exp_times == [exp_times, exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter

    async def test_configure_filter_as_number(self):
        async with self.make_script():
            exp_times = [0, 2, 0.5]
            filter = 2
            image_type = "OBJECT"
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                filter=filter,
            )
            assert self.script.config.exp_times == exp_times
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter

    async def test_configure_fails_missing_image_type(self):
        async with self.make_script():
            exp_times = [0, 2, 0.5]
            image_type = "OBJECT"
            nimages = len(exp_times) + 1
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(
                    exp_times=exp_times, image_type=image_type, nimages=nimages
                )

    async def run_take_images_test(
        self, mock_ready_to_take_data=None, expect_exception=None
    ):
        async with self.make_script():
            self.script.camera.ready_to_take_data = mock_ready_to_take_data
            # instead of mocking camera.take_imgtype mock expose
            self.script.camera.expose = unittest.mock.AsyncMock()
            self.script.camera.setup_instrument = unittest.mock.AsyncMock()

            nimages = 5

            config = await self.configure_script(
                nimages=nimages,
                exp_times=1.0,
                image_type="OBJECT",
                filter=1,
            )

            if expect_exception is not None:
                await self.run_script(expected_final_state=Script.ScriptState.FAILED)
                self.assertEqual(self.script.state.state, Script.ScriptState.FAILED)
                self.assertIn(
                    str(mock_ready_to_take_data.side_effect), self.script.state.reason
                )
            else:
                await self.run_script()
                self.assertEqual(self.script.state.state, Script.ScriptState.DONE)

            if mock_ready_to_take_data is not None:
                if expect_exception:
                    mock_ready_to_take_data.assert_awaited_once()
                else:
                    self.assertEqual(mock_ready_to_take_data.await_count, nimages)
            else:
                with self.assertRaises(AttributeError):
                    self.script.camera.ready_to_take_data.assert_not_called()

            if expect_exception is None:
                assert nimages == config.nimages

                # Define the expected calls: first with filter=1 which is
                # first called in BaseTakeImage run method, the rest
                # happens in (take_imgtype x nimages) without arguments
                expected_calls = [unittest.mock.call(filter=1)] + [
                    unittest.mock.call()
                ] * nimages

                self.script.camera.setup_instrument.assert_has_awaits(
                    expected_calls, any_order=False
                )

    async def test_take_images(self):
        await self.run_take_images_test()

    async def test_take_images_tcs_ready(self):
        mock_ready = unittest.mock.AsyncMock(return_value=None)
        await self.run_take_images_test(mock_ready_to_take_data=mock_ready)

    async def test_take_images_tcs_not_ready(self):
        mock_ready = unittest.mock.AsyncMock(side_effect=RuntimeError("TCS not ready"))
        await self.run_take_images_test(
            mock_ready_to_take_data=mock_ready, expect_exception=RuntimeError
        )

    async def test_executable_comcam(self):
        """Test that the script is executable for ComCam."""
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_image_comcam.py"
        await self.check_executable(script_path)

    async def test_executable_lsstcam(self) -> None:
        """Test that the script is executable for LSSTCam."""
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_image_lsstcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
