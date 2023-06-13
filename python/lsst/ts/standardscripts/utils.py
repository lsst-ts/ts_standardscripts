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

__all__ = [
    "get_scripts_dir",
    "get_s3_bucket",
    "get_topic_time_utc",
    "format_as_list",
    "format_grid",
]

import collections.abc
import os
import pathlib

import numpy as np
from lsst.ts import salobj
from lsst.ts.utils import astropy_time_from_tai_unix

S3_INSTANCES = dict(
    tucson="tuc",
    base="ls",
    summit="cp",
)


def get_scripts_dir():
    """Get the absolute path to the scripts directory.

    Returns
    -------
    scripts_dir : `pathlib.Path`
        Absolute path to the specified scripts directory.

    """
    return pathlib.Path(__file__).resolve().parent / "data" / "scripts"


def get_s3_bucket() -> salobj.AsyncS3Bucket:
    """Generate an s3 bucket object.

    The method will try to determine the s3 instance from the LSST_SITE
    environment variable. If it can't it will use "mock" as the instance
    value and will also mock the s3 bucket. This is useful for unit testing.
    """

    site = os.environ.get("LSST_SITE")
    do_mock = site not in S3_INSTANCES
    s3instance = S3_INSTANCES.get(site, "mock")

    s3bucket_name = salobj.AsyncS3Bucket.make_bucket_name(
        s3instance=s3instance,
    )

    return salobj.AsyncS3Bucket(
        name=s3bucket_name,
        domock=do_mock,
        create=do_mock,
    )


def format_as_list(value, recurrences):
    """
    Reformat single instance of the attribute `value` as a list with
    a specified number of recurrences .

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


def format_grid(
    axis1: float | list[float], axis2: float | list[float]
) -> tuple[list[float], list[float]]:
    """Format two input values into lists with the same lengths.

    If both values are scalars, the return value will be a pair of lists with
    a single value.

    If one of the inputs is a scalar and the other is a list, the return value
    is a list with the scalar value with the same length as the list and the
    list itself.

    If both are lists with the same dimension, the return value is the same as
    the input. However, if the lists have different dimensions an exception is
    raised.

    Parameters
    ----------
    axis1 : `float` or `list`[`float`]
        Input value for the first axis.
    axis2 : `float` or `list`[`float`]
        Input value for the second axis.

    Returns
    -------
    `tuple`[`list`[`float`], `list`[`float`]]]
        Pair of lists with the same length.

    Raises
    ------
    RuntimeError
        If both inputs are lists of different lengths.
    """
    if np.isscalar(axis1) and np.isscalar(axis2):
        return [axis1], [axis2]
    elif np.isscalar(axis1):
        return format_as_list(axis1, len(axis2)), axis2
    elif np.isscalar(axis2):
        return axis1, format_as_list(axis2, len(axis1))
    else:
        if len(axis1) != len(axis2):
            raise RuntimeError(
                f"Array sizes must be the same. Got {len(axis1)} and {len(axis2)}."
            )
        return axis1, axis2


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
