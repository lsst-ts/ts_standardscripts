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

from lsst.ts.standardscripts.maintel import TakeAOSSequenceBalancedComCam

from .test_maintel_take_aos_sequence_comcam import TestTakeAOSSequenceComCam


class TestTakeAOSSequenceBalancedComCam(TestTakeAOSSequenceComCam):
    ScriptClass = TakeAOSSequenceBalancedComCam
    scriptName = "take_aos_sequence_balanced_comcam.py"


if __name__ == "__main__":
    unittest.main()
