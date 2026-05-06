# This file is part of ts_standardscripts.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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

import os
import unittest

import pytest
from lsst.ts import salobj
from lsst.ts.standardscripts.base_script_test_case import BaseScriptTestCase
from lsst.ts.standardscripts.system_wide_shutdown import SystemWideShutdown
from lsst.ts.standardscripts.utils import find_running_instances, get_scripts_dir
from lsst.ts.xml.enums import Script


class TestSystemWideShutdown(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["LSST_SITE"] = "test"

    def setUp(self) -> None:
        self.make_test_cscs = False
        self.ntest = 3
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = SystemWideShutdown(index=index)

        self.mock_test = (
            [salobj.TestCsc(index=c_id + 1) for c_id in range(self.ntest)]
            if self.make_test_cscs
            else []
        )

        return (self.script, *self.mock_test)

    async def test_shutdown(self):
        self.make_test_cscs = True

        async with self.make_script():
            components_running = dict(
                Test=[i + 1 for i in range(self.ntest)],
            )
            for component in components_running:
                indices = components_running[component]
                await self.script.shutdown(component=component, indices=indices)

            assert len(self.script.failed) == 0.0
            for mock_test in self.mock_test:
                assert mock_test.summary_state == salobj.State.OFFLINE

    async def test_ignore_indexed_components(self):
        self.make_test_cscs = True

        async with self.make_script():
            ignored_index = 2
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=[f"Test:{ignored_index}"],
            )

            await self.run_script()

            assert len(self.script.failed) == 0.0

            for i, mock_test in enumerate(self.mock_test):
                if i + 1 == ignored_index:
                    assert mock_test.summary_state != salobj.State.OFFLINE
                else:
                    assert mock_test.summary_state == salobj.State.OFFLINE

    async def test_ignore_indexed_components_fail_invalid_index(self):
        self.make_test_cscs = True

        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Test:a"],
            )

            await self.run_script(expected_final_state=Script.ScriptState.FAILED)

    async def test_ignore_indexed_components_fail_non_index_with_index(self):
        self.make_test_cscs = True

        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["MTMount:1"],
            )

            await self.run_script(expected_final_state=Script.ScriptState.FAILED)

    async def test_ignore_indexed_components_fail_conflicts(self):
        self.make_test_cscs = True

        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Test", "Test:1"],
            )

            await self.run_script(expected_final_state=Script.ScriptState.FAILED)

    async def test_discover(self):
        self.make_test_cscs = True

        async with self.make_script():
            components_alive = await self.script.discover_components()

            assert "Test" in components_alive
            assert set(components_alive.pop("Test")) == {
                i + 1 for i in range(self.ntest)
            }
            assert len(components_alive) == 0

    async def test_find_running_instances(self):
        self.make_test_cscs = True

        async with self.make_script():
            component, component_indices = await find_running_instances(
                self.script.domain, "Test"
            )

            assert component == "Test"
            assert set(component_indices) == {i + 1 for i in range(self.ntest)}

    async def test_find_running_instances_not_running(self):
        async with self.make_script():
            component, component_indices = await find_running_instances(
                self.script.domain, "Test"
            )

            assert component == "Test"
            assert component_indices == []

    async def test_configure(self):
        configs_good = [
            dict(
                user="Tester",
                reason="Unit test",
            ),
            dict(user="Tester", reason="Unit test", ignore=["Test"]),
            dict(user="Tester", reason="Unit test", start_with=["Test"]),
            dict(user="Tester", reason="Unit test", end_with=["Test"]),
            dict(
                user="Tester",
                reason="Unit test",
                ignore=["Test"],
                start_with=["Watcher"],
                end_with=["ScriptQueue"],
            ),
            dict(
                user="Tester",
                reason="Unit test",
                ignore=["Test:1"],
            ),
        ]

        for config in configs_good:
            with self.subTest(config=config):
                async with self.make_script():
                    await self.configure_script(**config)
                    assert self.script.config.user == config.get("user")
                    assert self.script.config.reason == config.get("reason")
                    assert self.script.config.ignore == config.get("ignore", [])
                    assert self.script.config.start_with == config.get("start_with", [])
                    assert self.script.config.end_with == config.get("end_with", [])

        configs_bad = [
            dict(
                reason="No user",
            ),
            dict(
                user="Test",
            ),
        ]

        for config in configs_bad:
            with self.subTest(config=config):
                async with self.make_script():
                    with pytest.raises(salobj.ExpectedError):
                        await self.configure_script(**config)

    async def test_check_ignored_components_valid(self):
        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Test"],
            )
            await self.script.check_ignored_components()

            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Test:1", "Test:2"],
            )
            await self.script.check_ignored_components()

    async def test_check_ignored_components_invalid_index(self):
        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Test:invalid"],
            )
            with pytest.raises(ValueError, match="Invalid index"):
                await self.script.check_ignored_components()

    async def test_check_ignored_components_non_indexed(self):
        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Watcher:1"],
            )
            with pytest.raises(ValueError, match="not indexed"):
                await self.script.check_ignored_components()

    async def test_check_ignored_components_conflict(self):
        async with self.make_script():
            await self.configure_script(
                user="Tester",
                reason="Unit test",
                ignore=["Test", "Test:1"],
            )
            with pytest.raises(ValueError, match="Cannot ignore both"):
                await self.script.check_ignored_components()

    async def test_run(self):
        self.make_test_cscs = True

        async with self.make_script():
            await self.configure_script(user="Tester", reason="Unit test.")

            await self.run_script()

            assert len(self.script.failed) == 0.0
            for mock_test in self.mock_test:
                assert mock_test.summary_state == salobj.State.OFFLINE

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "system_wide_shutdown.py"
        await self.check_executable(script_path)
