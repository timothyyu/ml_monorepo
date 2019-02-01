import os
from contextlib import contextmanager
import logging


@contextmanager
def changedir(newdir):
    olddir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(olddir)


class BaseReader(object):
    """Abstract base class to inherit reader from. Reader load necessary objects
    (scenario, runhistory, trajectory) from files for different formats."""

    def __init__(self, folder, ta_exec_dir):
        self.logger = logging.getLogger("cave.reader")
        self.folder = folder
        self.ta_exec_dir = ta_exec_dir

        self.scen = None

    def get_scenario(self):
        """Expects `self.folder/scenario.txt` with appropriately formatted
        scenario-information (
        `<https://automl.github.io/SMAC3/stable/options.html#scenario>`_)"""
        raise NotImplemented()

    def get_runhistory(self):
        """Create RunHistory-object from files."""
        raise NotImplemented()

    def get_validated_runhistory(self):
        """Create validated runhistory from files, if available."""
        raise NotImplemented()

    def get_trajectory(self):
        """Create trajectory (list with dicts as entries)"""
        raise NotImplemented()
