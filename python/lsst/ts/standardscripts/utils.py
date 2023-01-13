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

__all__ = ["get_scripts_dir", "get_topic_time_utc"]

import collections.abc
import pathlib

from lsst.ts.utils import astropy_time_from_tai_unix


def get_scripts_dir():
    """Get the absolute path to the scripts directory.

    Returns
    -------
    scripts_dir : `pathlib.Path`
        Absolute path to the specified scripts directory.

    """
    return pathlib.Path(__file__).resolve().parent / "data" / "scripts"


def format_as_list(value, recurrences):
    """
    Reformat single instance of the attribute `value` as a list with
    a specified number of reccurances.

    Configurations often allow a single value for an attribute to be passed
    that needs to be replicated as a list. This occurs when the (YAML) type
    is specified as an array but a user provides a single value
    (as a float/int/string etc). For example, an instrument setup for 5
    different exposure times may only be given a single value for filter.
    However, often the single filter value needs to be reformatted of a
    list of length 5.

    This function returns the input as a list, with the desired
    of recurrences.

    Parameters
    ----------
    value: `str, float, int, boolean`
        A single element of any type. Must not be a list.
    recurrences: `int`
        An integer specifying the number of occurrences and length of the
        returned list

    Returns
    -------
    value_as_list: `list`
        A list of length `recurrences`, where all elements are the input
        parameter `value`
    """

    # Check to see if the input data is iterable (not a scalar)
    # Strings are iterable, so check if it's a string as well
    if isinstance(value, collections.abc.Iterable) and not isinstance(value, str):

        # Verify that the array is the correct number of recurrences
        # if specified as a list then it should already have the
        # correct number of instances.
        if len(value) != recurrences:
            raise ValueError(
                f"The input data {value} is already an array of "
                f"length {len(value)}, "
                "but the length does not match the number of "
                f"desired reccurences ({recurrences}). "
                "Verify that all inputs are singular values or"
                "have the correct length(s) values."
            )
        else:
            # input already an iterable array with correct
            # number of elements, so just return the array
            return value

    # value is a scalar, convert to a list repeating the scalar value
    value_as_list = [value] * recurrences

    return value_as_list


def get_topic_time_utc(topic):
    """Reformat a topic command time from TAI unix to UTC.

    Parameters
    ----------
    topic: `salobj.BaseMsgType`
        A single event message.

    Returns
    -------
    topic_time_utc: `str`
        Value of salobj.BaseMsgType.private_sndStamp in UTC str time.
    """

    topic_time = astropy_time_from_tai_unix(topic.private_sndStamp)
    topic_time.format = "iso"
    topic_time_utc = topic_time.utc
    return topic_time_utc
