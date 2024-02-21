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

from lsst.ts import standardscripts
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
                camera=camera, config=dict(), identifier=cam
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
                camera=camera, config=dict(), identifier=f"GenericCam_{i}"
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
            The expected configuration dictionary for the camera.
        """
        camera_setup_found = False

        camera_setup = self.script.camera_setups.get(camera_setup_key)
        if camera_setup:
            camera_setup_config = camera_setup.config
            assert (
                camera_setup_config == expected_config
            ), f"Configuration mismatch for {camera_setup_key}"
            camera_setup_found = True

        assert (
            camera_setup_found
        ), f"{camera_setup_key} setup missing or incorrect in camera_setups."

    async def test_configure_with_only_lsstcam(self):
        lsstcam_config = {
            "exp_times": [15, 30, 45],
            "image_type": "OBJECT",
            "filter": "r",
        }
        config = {
            "lsstcam": lsstcam_config,
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

            # Assert that ComCam config is empty
            comcam_setup = self.script.camera_setups.get("comcam")
            if comcam_setup:
                assert comcam_setup.config == dict()

    async def test_configure_with_only_comcam(self):
        comcam_config = {
            "exp_times": 15,
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
                "exp_times": [15, 30, 45, 60, 75, 90],
                "image_type": "OBJECT",
                "filter": None,
            },
            "gencam": [
                {"index": 101, "exp_times": 5, "image_type": "OBJECT"},
                {"index": 102, "exp_times": [15, 35, 60], "image_type": "OBJECT"},
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
                "filter": "r",
            },
            "gencam": [
                {"index": 101, "exp_times": 5, "image_type": "OBJECT"},
                {
                    "index": 102,
                    "exp_times": [15, 30, 60, 90, 120],
                    "image_type": "OBJECT",
                },
            ],
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
                {"index": 102, "exp_times": 5, "image_type": "OBJECT"},
                {"index": 103, "exp_times": [15, 30], "image_type": "OBJECT"},
            ],
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

    def normalize_exp_times(self, exp_times):
        """Ensure exp_times is always treated as a list,
        even for single values or zero.
        """
        # Adjust to handle a single zero value or non-list exp_times
        if not isinstance(exp_times, list) or exp_times == 0:
            return [exp_times]
        return exp_times

    def validate_camera_configuration(self, cam_config, cam_key=None):
        """Validates the camera setup and call counts based on its
        configuration.

        Parameters
        ----------
        cam_config : dict
            The configuration for the camera setup.
        cam_key : str, optional
            The camera setup key, if different from the camera identifier.
        """
        if isinstance(cam_config, dict) and "exp_times" in cam_config:
            # Normalize exp_times to ensure it's a list
            exp_times = cam_config["exp_times"]
            if not isinstance(exp_times, list):
                exp_times = [exp_times]

            # Calculate expected_calls considering zero as valid exposure
            expected_calls = len([exp for exp in exp_times if exp >= 0])

            # Retrieve the appropriate camera setup
            camera_key = (
                cam_key if cam_key else f"generic_camera_{cam_config.get('index')}"
            )
            camera_setup = self.script.camera_setups.get(camera_key)

            if camera_setup:
                actual_calls = camera_setup.camera.take_imgtype.await_count
                self.assertEqual(
                    actual_calls,
                    expected_calls,
                    f"Expected {expected_calls} calls for {camera_key}, but got {actual_calls}.",
                )

                # Validate the filter setup if applicable
                if "filter" in cam_config:
                    camera_setup.camera.setup_instrument.assert_awaited_once_with(
                        filter=cam_config["filter"]
                    )
            else:
                raise AssertionError(f"Camera setup for {camera_key} not found.")
        else:
            raise ValueError(
                f"Invalid configuration for {cam_key}. Configuration must be a dictionary with 'exp_times'."
            )

    async def test_run_block(self):
        async with self.make_script():
            # Cnfiguration for LSSTCam, ComCam, and generic cameras
            config = {
                "lsstcam": {"exp_times": [10, 20], "image_type": "OBJECT"},
                "gencam": [
                    {"index": 101, "exp_times": [5, 5], "image_type": "DARK"},
                    {"index": 102, "exp_times": 0, "image_type": "BIAS"},
                ],
                "reason": "SITCOM-321",
                "program": "BLOCK-123",
                "note": "Test image",
            }

            await self.configure_script(**config)
            await self.run_script()

            # Validate configurations and calls for each configured camera
            for cam_key, cam_config in config.items():
                if cam_key == "gencam":  # gencam is a list of dictionaries
                    for gencam_config in cam_config:
                        self.validate_camera_configuration(gencam_config)
                elif cam_key in [
                    "lsstcam",
                    "comcam",
                ]:  # lsstcam and comcam are dictionaries
                    self.validate_camera_configuration(config[cam_key], cam_key)

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_image_anycam.py"
        await self.check_executable(script_path)
