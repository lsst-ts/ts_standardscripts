from lsst.ts.standardscripts.utils import get_scripts_dir as core_get_scripts_dir


def get_scripts_dir():
    """
    Override the core get_scripts_dir function for Maintel usage.

    Returns
    -------
    pathlib.Path
        Path to Maintel's data/scripts directory
    """
    return core_get_scripts_dir(file_path=__file__)
