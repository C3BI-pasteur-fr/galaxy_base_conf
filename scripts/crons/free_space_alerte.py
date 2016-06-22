"""
Created on Feb. 24, 2016

@authors: Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
Send a mail alert if available space from a given space is less than 10%
"""
import os
import argparse
from lib_cron import sendmail
from lib_cron import ADMINS_EMAILS

def get_totalspace(statvfs):
    """
    Use a statvfs_result object whose attributes describe the filesystem to return the total size of a file system
    :param statvfs: statvfs_result object
    :return: float
    """
    return float(statvfs.f_frsize) * float(statvfs.f_blocks)


def get_availspace(statvfs):
    """
    Use a statvfs_result object whose attributes describe the filesystem to return the available size of a file system
    :param statvfs: statvfs_result object
    :return: float
    """
    return float(statvfs.f_frsize) * float(statvfs.f_bavail)


def get_statsystem(nfsmount):
    """
    Perform a statvfs() system call on the given path. The return value is an object whose attributes describe the
    filesystem on the given path, and correspond to the members of the statvfs structure, namely: f_bsize, f_frsize,
    f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail, f_flag, f_namemax.
    :param nfsmount: Path
    :return: statvfs_result object
    """
    return os.statvfs(nfsmount)


def get_percentfree(avail, total):
    """
    Return the result of the operation avail/total * 100
    :param avail: float
    :param total: float
    :return: float
    """
    return avail/total * 100


def alert(percent):
    """
    Send a mail alert if percent is greater than 10
    :param percent:
    :return: None
    """
    if percent < 15:
        sendmail(ADMINS_EMAILS,"Only {0:.2f}% of space disk are available".format(percent), "Galaxy File system alert")
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--path", help="path to monitor")
    args = parser.parse_args()

    stat = get_statsystem(args.path)
    total_space = get_totalspace(stat)
    available_space = get_availspace(stat)
    percent_available = get_percentfree(available_space, total_space)
    alert(percent_available)
