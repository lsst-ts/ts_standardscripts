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

import contextlib
import os
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.standardscripts.dummy_block_script import DummyBlockScript
from lsst.ts.utils import ImageNameServiceClient


class TestBaseBlockScript(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test BaseBlockScript using the DummyBlockScript script."""

    async def basic_make_script(self, index):
        self.script = DummyBlockScript(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.components_attr = ["mtm1m3"]
            yield

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_fail_test_case_name_only(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(name="LVV-T2190")
            with pytest.raises(
                salobj.ExpectedError, match="'execution' is a required property"
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    pause_for=pause_for,
                    program=program,
                    reason=reason,
                    test_case=test_case,
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_fail_test_case_execution_only(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(execution="LVV-E2390")
            with pytest.raises(
                salobj.ExpectedError, match="'name' is a required property"
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    pause_for=pause_for,
                    program=program,
                    reason=reason,
                    test_case=test_case,
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_fail_test_case_version_only(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(version="1.0")
            with pytest.raises(
                salobj.ExpectedError, match="'name' is a required property"
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    pause_for=pause_for,
                    program=program,
                    reason=reason,
                    test_case=test_case,
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_fail_test_case_name_execution_only(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(name="LVV-T2190", execution="LVV-E2390")
            with pytest.raises(
                salobj.ExpectedError, match="'version' is a required property"
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    pause_for=pause_for,
                    program=program,
                    reason=reason,
                    test_case=test_case,
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_fail_test_case_name_version_only(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(name="LVV-T2190", version="1.0")
            with pytest.raises(
                salobj.ExpectedError, match="'execution' is a required property"
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    pause_for=pause_for,
                    program=program,
                    reason=reason,
                    test_case=test_case,
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_fail_test_case_program_version_only(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(execution="LVV-E2390", version="1.0")
            with pytest.raises(
                salobj.ExpectedError, match="'name' is a required property"
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    pause_for=pause_for,
                    program=program,
                    reason=reason,
                    test_case=test_case,
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_reason_program(self) -> None:
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            await self.configure_script(
                az=az,
                el=el,
                pause_for=pause_for,
                program=program,
                reason=reason,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert self.script.test_case is None
            assert (
                self.script.checkpoint_message
                == "DummyBlockScript BLOCK-123 202306060001 SITCOM-321"
            )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_reason_program_test_case(self) -> None:
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(name="LVV-T2190", execution="LVV-E2390", version="1.0")

            await self.configure_script(
                az=az,
                el=el,
                pause_for=pause_for,
                program=program,
                reason=reason,
                test_case=test_case,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert self.script.test_case["name"] == test_case["name"]
            assert self.script.test_case["execution"] == test_case["execution"]
            assert self.script.test_case["version"] == test_case["version"]
            assert "initial_step" not in self.script.test_case
            assert "project" not in self.script.test_case
            assert (
                self.script.checkpoint_message
                == "DummyBlockScript BLOCK-123 202306060001 SITCOM-321"
            )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_reason_program_test_case_initial_step(self) -> None:
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(
                name="LVV-T2190", execution="LVV-E2390", version="1.0", initial_step=10
            )

            await self.configure_script(
                az=az,
                el=el,
                pause_for=pause_for,
                program=program,
                reason=reason,
                test_case=test_case,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert self.script.test_case["name"] == test_case["name"]
            assert self.script.test_case["execution"] == test_case["execution"]
            assert self.script.test_case["version"] == test_case["version"]
            assert self.script.test_case["initial_step"] == test_case["initial_step"]
            assert "project" not in self.script.test_case
            assert (
                self.script.checkpoint_message
                == "DummyBlockScript BLOCK-123 202306060001 SITCOM-321"
            )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_reason_program_test_case_project(self) -> None:
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            test_case = dict(
                name="LVV-T2190", execution="LVV-E2390", version="1.0", project="SITCOM"
            )

            await self.configure_script(
                az=az,
                el=el,
                pause_for=pause_for,
                program=program,
                reason=reason,
                test_case=test_case,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert self.script.test_case["name"] == test_case["name"]
            assert self.script.test_case["execution"] == test_case["execution"]
            assert self.script.test_case["version"] == test_case["version"]
            assert "initial_step" not in self.script.test_case
            assert self.script.test_case["project"] == test_case["project"]
            assert (
                self.script.checkpoint_message
                == "DummyBlockScript BLOCK-123 202306060001 SITCOM-321"
            )

    @unittest.mock.patch.dict(os.environ, {"LSST_SITE": "summit"})
    @unittest.mock.patch.object(
        ImageNameServiceClient,
        "get_next_obs_id",
        return_value=(None, ["BL123-202306060001"]),
    )
    async def test_get_obs_id_block_ticket(self, mock_get_next_obs_id):
        async with self.make_dry_script():
            program = "BLOCK-123"
            self.script.program = program

            obs_id = await self.script.get_obs_id()
            assert obs_id is not None
            assert obs_id.startswith("BL123")

    # Assuming obs_is for test cases will start with BT
    @unittest.mock.patch.dict(os.environ, {"LSST_SITE": "summit"})
    @unittest.mock.patch.object(
        ImageNameServiceClient,
        "get_next_obs_id",
        return_value=(None, ["BT123-202306060001"]),
    )
    async def test_get_obs_id_block_test_case(self, mock_get_next_obs_id):
        async with self.make_dry_script():
            program = "BLOCK-T123"
            self.script.program = program

            obs_id = await self.script.get_obs_id()
            assert obs_id is not None
            assert obs_id.startswith("BT123")

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_reason_program_block_test_case(self) -> None:
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-T123"
            reason = "SITCOM-321"
            test_case = dict(
                name="BLOCK-T2190",
                execution="BLOCK-E2390",
                version="1.0",
                project="SITCOM",
            )

            await self.configure_script(
                az=az,
                el=el,
                pause_for=pause_for,
                program=program,
                reason=reason,
                test_case=test_case,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert self.script.test_case["name"] == test_case["name"]
            assert self.script.test_case["execution"] == test_case["execution"]
            assert self.script.test_case["version"] == test_case["version"]
            assert "initial_step" not in self.script.test_case
            assert self.script.test_case["project"] == test_case["project"]
            assert (
                self.script.checkpoint_message
                == "DummyBlockScript BLOCK-T123 202306060001 SITCOM-321"
            )

    async def test_run_no_test_case(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            ra = [0.0, 10.0, 20.0]
            dec = [80.0, 70.0, 60.0]
            timeout = 100.0
            program = "BLOCK-T123"
            reason = "SITCOM-321"

            await self.configure_script(
                ra=ra,
                dec=dec,
                program=program,
                reason=reason,
                move_timeout=timeout,
            )

            await self.run_script()

            expected_calls = [
                unittest.mock.call(ra=_ra, dec=_dec, timeout=timeout)
                for _ra, _dec in zip(ra, dec)
            ]
            self.script.mtcs.dummy_move_radec.assert_has_awaits(expected_calls)

            assert not self.script.evt_largeFileObjectAvailable.has_data

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_run_with_test_case(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            ra = [0.0, 10.0, 20.0]
            dec = [80.0, 70.0, 60.0]
            program = "BLOCK-T123"
            reason = "SITCOM-321"
            timeout = 100.0
            test_case = dict(
                name="BLOCK-T2190",
                execution="BLOCK-E2390",
                version="1.0",
                project="BLOCK",
            )

            await self.configure_script(
                ra=ra,
                dec=dec,
                program=program,
                reason=reason,
                test_case=test_case,
                move_timeout=timeout,
            )

            await self.run_script()

            expected_calls = [
                unittest.mock.call(ra=_ra, dec=_dec, timeout=timeout)
                for _ra, _dec in zip(ra, dec)
            ]
            self.script.mtcs.dummy_move_radec.assert_has_awaits(expected_calls)

            assert len(self.script.step_results) == len(ra)
            assert self.script.evt_largeFileObjectAvailable.has_data
            assert self.script.evt_largeFileObjectAvailable.data.id == "202306060001"
            assert self.script.evt_largeFileObjectAvailable.data.url.endswith(
                f"{test_case['name']}_202306060001.json"
            )
            assert (
                self.script.evt_largeFileObjectAvailable.data.generator
                == test_case["name"]
            )
            assert self.script.evt_largeFileObjectAvailable.data.mimeType == "JSON"
            assert self.script.evt_largeFileObjectAvailable.data.byteSize > 0

            for test_step in self.script.step_results:
                assert test_step["status"] == "PASSED"

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_run_fail_with_test_case(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )
            self.script.mtcs.configure_mock(
                **{
                    "dummy_move_radec.side_effect": [
                        None,
                        RuntimeError("Something went wrong."),
                    ]
                }
            )

            ra = [0.0, 10.0, 20.0]
            dec = [80.0, 70.0, 60.0]
            program = "BLOCK-123"
            reason = "SITCOM-321"
            timeout = 1200.0
            test_case = dict(
                name="LVV-T2190", execution="LVV-E2390", version="1.0", project="SITCOM"
            )

            await self.configure_script(
                ra=ra,
                dec=dec,
                program=program,
                reason=reason,
                test_case=test_case,
                move_timeout=timeout,
            )

            with pytest.raises(AssertionError):
                await self.run_script()

            expected_calls = [
                unittest.mock.call(ra=_ra, dec=_dec, timeout=timeout)
                for _ra, _dec in zip(ra, dec)
            ]
            expected_calls.pop(-1)
            self.script.mtcs.dummy_move_radec.assert_has_awaits(expected_calls)

            assert len(self.script.step_results) == len(ra) - 1
            assert self.script.evt_largeFileObjectAvailable.has_data
            assert self.script.evt_largeFileObjectAvailable.data.id == "202306060001"
            assert self.script.evt_largeFileObjectAvailable.data.url.endswith(
                f"{test_case['name']}_202306060001.json"
            )
            assert (
                self.script.evt_largeFileObjectAvailable.data.generator
                == test_case["name"]
            )
            assert self.script.evt_largeFileObjectAvailable.data.mimeType == "JSON"
            assert self.script.evt_largeFileObjectAvailable.data.byteSize > 0

            for test_step, expected_status in zip(
                self.script.step_results, ["PASSED", "FAILED"]
            ):
                assert test_step["status"] == expected_status
