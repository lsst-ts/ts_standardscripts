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

import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.standardscripts.maintel import CameraSetup, TakeImageAnyCam


class TestTakeImageAnyCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeImageAnyCam(index=index)

        self.mock_mtcs()
        self.mock_cameras()

        return (self.script,)

    def mock_mtcs(self):
        """Mock MTCS instances and its methods."""
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.mtcs.assert_liveliness = unittest.mock.AsyncMock()
        self.script.mtcs.components_attr = ["mtm1m3"]

        # Initialize camera_setups with mock cameras
        self.script.camera_setups = {}

    def mock_cameras(self):
        """Mock cameras (ComCam, LSSTCam, Generic Cameras) with
        their methods and attributes
        """
        # Mocking main cameras
        for cam in ["LSSTCam", "ComCam"]:
            camera = unittest.mock.AsyncMock(name=f"{cam}")
            camera.assert_liveliness = unittest.mock.AsyncMock()
            camera.assert_all_enabled = unittest.mock.AsyncMock()
            camera.take_imgtype = unittest.mock.AsyncMock()
            camera.setup_instrument = unittest.mock.AsyncMock()
            camera.read_out_time = 2
            camera.shutter_time = 0.1
            self.script.camera_setups[cam.lower()] = CameraSetup(
                camera=camera,
                config=dict(),
                identifier=cam,
                normalize=False,
            )

        # Mocking generic cameras
        for i in [101, 102, 103]:
            gen_cam_key = f"generic_camera_{i}"
            camera = unittest.mock.AsyncMock(name=f"GenericCam_{i}")
            camera.assert_liveliness = unittest.mock.AsyncMock()
            camera.assert_all_enabled = unittest.mock.AsyncMock()
            camera.take_imgtype = unittest.mock.AsyncMock()
            camera.read_out_time = 1
            camera.shutter_time = 0.1
            self.script.camera_setups[gen_cam_key] = CameraSetup(
                camera=camera,
                config=dict(),
                identifier=f"GenericCam_{i}",
                normalize=False,
            )

    async def assert_camera_setup(self, camera_setup_key, expected_config):
        """
        Helper method to assert that a CameraSetup for a given camera
        identifier has been correctly configured.

        Parameters
        ----------
        camera_setup_key : str
            The camera setup key of the camera to check ("lsstcam", "comcam",
            "generic_camera_1", "generic_camera_2", "generic_camera_3").
        expected_config : dict
            The expected configuration dictionary for the camera, before
            normalization.
        """
        camera_setup_found = False

        # Normalize the expected configuration to ensure it matches
        # the format stored within CameraSetup objects.
        normalized_expected_config = CameraSetup.normalize_config(expected_config)

        camera_setup = self.script.camera_setups.get(camera_setup_key)
        if camera_setup:
            camera_setup_config = camera_setup.config
            assert camera_setup_config == normalized_expected_config, (
                f"Configuration mismatch for {camera_setup_key}: expected "
                f"{normalized_expected_config}, got {camera_setup_config}"
            )
            camera_setup_found = True

        assert (
            camera_setup_found
        ), f"{camera_setup_key} setup missing or incorrect in camera_setups."

    async def test_config_ignore(self):
        # Testing ignored components
        lsstcam_config = {
            "exp_times": 5,
            "nimages": 5,
            "image_type": "OBJECT",
            "filter": "r",
        }
        config = {
            "lsstcam": lsstcam_config,
            "reason": "SITCOM-321",
            "program": "BLOCK-123",
            "note": "Test image",
            "ignore": ["mtm1m3", "no_comp"],
        }
        async with self.make_script():
            await self.configure_script(**config)

            # Asserting that component were ignored
            self.script.mtcs.disable_checks_for_components.assert_called_once_with(
                components=config["ignore"]
            )

    async def test_invalid_program_name(self):
        # Testing invalid program name
        bad_config = {
            "comcam": {
                "exp_times": [5, 15, 20],
                "nimages": 10,
                "image_type": "OBJECT",
                "filter": None,
            },
            "reason": "SITCOM-321",
            "program": "BLOCK123",
            "note": "Test image",
        }

        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(**bad_config)

    async def test_invalid_config_comcam(self):
        # Testing invalid exp_times and nimages entry
        bad_config = {
            "comcam": {
                "exp_times": [5, 15, 20],
                "nimages": 10,
                "image_type": "OBJECT",
                "filter": None,
            },
        }

        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(**bad_config)

    async def test_configure_with_only_lsstcam(self):
        lsstcam_config = {
            "exp_times": [15, 30, 45, 60, 75, 90],
            "image_type": "OBJECT",
            "filter": "r",
        }
        config = {
            "lsstcam": lsstcam_config,
            "reason": "SITCOM-321",
            "program": "BLOCK-123",
            "note": "Test image",
            "ignore": ["mtm1m3", "no_comp"],
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Asserting LSSTCam setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="lsstcam", expected_config=config["lsstcam"]
            )

            # Assert that ComCam config is empty
            comcam_setup = self.script.camera_setups.get("comcam")
            if comcam_setup:
                assert comcam_setup.config == dict()

    async def test_configure_with_only_comcam(self):
        comcam_config = {
            "exp_times": 15,
            "nimages": 10,
            "image_type": "OBJECT",
            "filter": 1,
        }
        config = {
            "comcam": comcam_config,
            "reason": "SITCOM-321",
            "program": "BLOCK-123",
            "note": "Test image",
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Asserting ComCam setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="comcam", expected_config=config["comcam"]
            )

            # Assert that LSSTCam config is empty
            lsstcam_setup = self.script.camera_setups.get("lsstcam")
            if lsstcam_setup:
                assert lsstcam_setup.config == dict()

    async def test_configure_with_lsstcam_and_generic_cams(self):
        config = {
            "lsstcam": {
                "exp_times": 0,
                "nimages": 30,
                "image_type": "BIAS",
            },
            "gencam": [
                {"index": 101, "exp_times": 5, "nimages": 10, "image_type": "OBJECT"},
                {"index": 102, "exp_times": 30, "nimages": 1, "image_type": "DARK"},
                {
                    "index": 103,
                    "exp_times": [5, 10, 20, 40, 60, 120],
                    "image_type": "FLAT",
                },
            ],
            "reason": "SITCOM-321",
            "program": "BLOCK-123",
            "note": "Test image",
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Asserting LSSTCam setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="lsstcam", expected_config=config["lsstcam"]
            )

            # Asserting GenericCam_101 setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="generic_camera_101",
                expected_config=config["gencam"][0],
            )

            # Asserting GenericCam_102 setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="generic_camera_102",
                expected_config=config["gencam"][1],
            )

            # Assert that ComCam config is empty
            comcam_setup = self.script.camera_setups.get("comcam")
            if comcam_setup:
                assert comcam_setup.config == dict()

    async def test_configure_with_comcam_and_generic_cams(self):
        config = {
            "comcam": {
                "exp_times": 30,
                "image_type": "OBJECT",
                "filter": None,
            },
            "gencam": [
                {"index": 101, "exp_times": 5, "image_type": "OBJECT"},
                {"index": 102, "exp_times": [15, 30, 60], "image_type": "OBJECT"},
                {"index": 103, "exp_times": 30, "nimages": 10, "image_type": "OBJECT"},
            ],
            "ignore": ["mtm1m3", "no_comp"],
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Asserting ComCam setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="comcam", expected_config=config["comcam"]
            )

            # Asserting GenericCam_101 setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="generic_camera_101",
                expected_config=config["gencam"][0],
            )

            # Asserting GenericCam_102 setup is correctly configured
            await self.assert_camera_setup(
                camera_setup_key="generic_camera_102",
                expected_config=config["gencam"][1],
            )

            # Assert that LSSTCam config is empty
            lsstcam_setup = self.script.camera_setups.get("lsstcam")
            if lsstcam_setup:
                assert lsstcam_setup.config == dict()

    async def test_configure_with_only_generic_cams(self):
        config = {
            "gencam": [
                {"index": 101, "exp_times": [15], "image_type": "OBJECT"},
                {"index": 102, "exp_times": 5, "nimages": 10, "image_type": "OBJECT"},
                {"index": 103, "exp_times": 0, "image_type": "BIAS"},
            ],
            "ignore": ["mtm1m3", "no_comp"],
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Asserting Generic Cameras setup are correctly configured
            await self.assert_camera_setup(
                camera_setup_key="generic_camera_101",
                expected_config=config["gencam"][0],
            )

            await self.assert_camera_setup(
                camera_setup_key="generic_camera_102",
                expected_config=config["gencam"][1],
            )

            await self.assert_camera_setup(
                camera_setup_key="generic_camera_103",
                expected_config=config["gencam"][2],
            )

            # Assert tha both LSSTCam and ComCam config are empty
            lsstcam_setup = self.script.camera_setups.get("lsstcam")
            if lsstcam_setup:
                assert lsstcam_setup.config == dict()

            comcam_setup = self.script.camera_setups.get("comcam")
            if comcam_setup:
                assert comcam_setup.config == dict()

    async def validate_camera_configuration(self, cam_config, cam_key=None):
        """Validates the camera setup and call counts based on its
        configuration, ensuring that expected configuration is
        normalized.
        """
        if "exp_times" not in cam_config:
            raise ValueError(
                f"Invalid configuration for {cam_key}. Configuration must include 'exp_times'."
            )

        # Normalize the expected configuration to match the script's
        # internal representation.
        normalized_cam_config = CameraSetup.normalize_config(cam_config.copy())

        # Calculate expected calls considering zero as valid exposure time
        expected_calls = len(
            [exp for exp in normalized_cam_config["exp_times"] if exp >= 0]
        )

        camera_key = cam_key if cam_key else f"generic_camera_{cam_config.get('index')}"
        camera_setup = self.script.camera_setups.get(camera_key)

        if not camera_setup:
            raise AssertionError(f"Camera setup for {camera_key} not found.")

        actual_calls = camera_setup.camera.take_imgtype.await_count
        assert (
            actual_calls == expected_calls
        ), f"Expected {expected_calls} calls for {camera_key}, got {actual_calls}."

        # Validate the filter setup if applicable
        if "filter" in normalized_cam_config:
            camera_setup.camera.setup_instrument.assert_awaited_once_with(
                filter=normalized_cam_config["filter"]
            )

    async def test_run_block(self):
        async with self.make_script():
            # Cnfiguration for LSSTCam, ComCam, and generic cameras
            config = {
                "lsstcam": {
                    "exp_times": 30,
                    "nimages": 10,
                    "image_type": "OBJECT",
                    "filter": None,
                },
                "gencam": [
                    {"index": 101, "exp_times": 30, "image_type": "DARK"},
                    {"index": 102, "exp_times": [15, 30, 60], "image_type": "OBJECT"},
                    {
                        "index": 103,
                        "exp_times": 30,
                        "nimages": 10,
                        "image_type": "OBJECT",
                    },
                ],
            }

            await self.configure_script(**config)
            await self.run_script()

            # Validate configurations and calls for each configured camera
            for cam_key, cam_config in config.items():
                if cam_key == "gencam":  # gencam is a list of dictionaries
                    for gencam_config in cam_config:
                        await self.validate_camera_configuration(gencam_config)
                else:  # lsstcam and comcam are dictionaries
                    await self.validate_camera_configuration(cam_config, cam_key)

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_image_anycam.py"
        await self.check_executable(script_path)
