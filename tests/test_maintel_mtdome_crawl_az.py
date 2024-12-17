# This file is part of ts_maintel_standardscripts
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

import asyncio
import unittest
from types import SimpleNamespace

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.maintel.standardscripts import get_scripts_dir
from lsst.ts.maintel.standardscripts.mtdome import CrawlAz, Direction
from lsst.ts.xml.enums.MTDome import SubSystemId


class TestCrawlAz(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = CrawlAz(index=index)

        self.script.mtdome = unittest.mock.AsyncMock()
        self.script.mtdome.configure_mock(
            **{
                "evt_summaryState.aget.side_effect": self.get_mtdome_summary_state,
                "evt_summaryState.next.side_effect": self.get_mtdome_summary_state,
            },
        )

        return (self.script,)

    async def get_mtdome_summary_state(self, timeout=0.0, flush=False):
        await asyncio.sleep(1.0)
        return SimpleNamespace(summaryState=salobj.State.ENABLED.value)

    async def test_configure_default(self):
        """Test the default configuration"""

        async with self.make_script():

            await self.configure_script()

            assert self.script.direction == Direction.ClockWise

    async def test_configure_clock_wise(self):
        """Test the default configuration"""

        async with self.make_script():

            await self.configure_script(direction="ClockWise")

            assert self.script.direction == Direction.ClockWise

    async def test_configure_counter_clock_wise(self):
        """Test the default configuration"""

        async with self.make_script():

            await self.configure_script(direction="CounterClockWise")

            assert self.script.direction == Direction.CounterClockWise

    async def test_configure_invalid_direction(self):
        """Test the default configuration"""

        async with self.make_script():

            with pytest.raises(
                salobj.ExpectedError, match="failed: 'InvalidDirection' is not one of"
            ):
                await self.configure_script(direction="InvalidDirection")

    async def test_run_with_default_config(self):
        async with self.make_script():

            await self.configure_script()

            # Once the script starts it will run forever until
            # stopped.
            run_script_task = asyncio.create_task(self.run_script())

            # wait a couple seconds than stop the script
            await asyncio.sleep(5.0)

            stop_data = self.script.cmd_stop.DataType()

            await self.script.do_stop(stop_data)

            await run_script_task

            expected_calls = [
                unittest.mock.call(
                    velocity=0.5,
                    timeout=self.script.TIMEOUT_CMD,
                ),
                unittest.mock.call(
                    velocity=0.0,
                    timeout=self.script.TIMEOUT_CMD,
                ),
            ]
            self.script.mtdome.cmd_crawlAz.set_start.assert_has_awaits(expected_calls)

            self.script.mtdome.cmd_stop.set_start.assert_awaited_with(
                subSystemIds=SubSystemId.AMCS,
                timeout=self.script.TIMEOUT_CMD,
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "mtdome" / "crawl_az.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
