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

__all__ = ["MuteAlarms"]

import yaml
from lsst.ts import salobj
from lsst.ts.xml.enums.Watcher import AlarmSeverity


class MuteAlarms(salobj.BaseScript):
    """
    Mute Watcher alarm(s) for a given amount of time.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index):
        super().__init__(
            index=index, descr="Mute Watcher alarm(s) for a given amount of time."
        )
        self.watcher = None
        self.std_timeout = 60.0

    @classmethod
    def get_schema(cls):
        schema_yaml = f"""
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/sleep.yaml
            title: MuteAlarms v1
            description: Configuration for MuteAlarms command.
            type: object
            properties:
                name:
                    description: >-
                        Name of alarm or alarms to mute.
                        Specify a regular expression for multiple alarms.
                    type: string
                mutedBy:
                    description: User who muted the alarm(s).
                    type: string
                duration:
                    description: Duration of the mute command in seconds.
                    type: number
                    minimum: 0
                    default: 300
                severity:
                    description: >-
                        Severity level being muted.
                        An AlarmSeverity enum.
                    type: string
                    enum: {[e.name for e in AlarmSeverity]}
                    default: "None"
            additionalProperties: false
            required:
                - name
                - mutedBy
                - duration
                - severity
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """
        self.name = config.name
        self.mutedBy = config.mutedBy
        self.duration = config.duration
        self.severity = AlarmSeverity[config.severity]

        # Create the Watcher remote
        if self.watcher is None:
            self.watcher = salobj.Remote(
                domain=self.domain,
                name="Watcher",
            )
            await self.watcher.start_task

    def set_metadata(self, metadata):
        metadata.duration = self.duration

    async def run(self):
        """Run the script."""
        self.log.info(f"Muting alarm(s) {self.name} for {self.duration} seconds.")
        await self.watcher.cmd_mute.set_start(
            name=self.name,
            duration=self.duration,
            severity=self.severity,
            mutedBy=self.mutedBy,
            timeout=self.std_timeout,
        )
