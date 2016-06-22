"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
chown output data
"""
import os
import sys
import argparse
import ldap3
from lib_cron import sendmail
from lib_cron import ADMINS_EMAILS, BASE_DN, ATTRS
sys.path.insert(0, os.path.dirname(__file__))


def init_connection(arguments):
    """
    Set connection
    :param arguments: args dictionnary
    :return: None
    """
    server = ldap3.Server(arguments.ldap_url, use_ssl=True, get_info=ldap3.ALL)
    with ldap3.Connection(server, auto_bind=True, check_names=True) as conn:
        set_output_files_permissions(arguments.base_output, conn)


def set_output_files_permissions(base_output, ldap_conn):
    """
    Set permissions to the outputs files for users
    :param base_output: outputs directory url
    :param ldap_conn: ldap connection object
    :return: None
    """
    try:
        folders_output = os.listdir(base_output)
    except OSError, e:
        sendmail(ADMINS_EMAILS, "Error {0}, {1} path doesn't exist\n".format(e, base_output), "Wrong base_output path")
        sys.exit(1)
    for folder in folders_output:
        if not folder.startswith('.'):
            user_directory = os.path.join(base_output, folder)
            user_uid, domain = folder.split('@')
            ldap_filter = '(& (objectclass=posixAccount) (uid={0}))'.format(user_uid)
            resp = ldap_conn.search(BASE_DN, ldap_filter, attributes=ATTRS)
            if resp:
                numeric_gid = ldap_conn.response[0]['attributes']['gidNumber']
                numeric_uid = ldap_conn.response[0]['attributes']['uidNumber']
                files = os.listdir(user_directory)
                for fi in files:
                    try:
                        output_file = os.path.join(user_directory, fi)
                        stat_file = os.stat(output_file)
                        uid_file = stat_file.st_uid
                        if user_uid != uid_file:
                            os.chown(output_file, numeric_uid, numeric_gid)
                    except OSError, e:
                        sendmail(ADMINS_EMAILS, "Error during chown of the file {0} in the output directory of"
                                                " {1} user.\n {2} \n".format(fi, folder, e),
                                 'Galaxy outputs files problem')
                        sys.exit(1)


if __name__ == "__main__":
    # Arguments parser
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--ldap_url', help='')
    parser.add_argument('--base_output', help='')
    args = parser.parse_args()
    init_connection(args)
