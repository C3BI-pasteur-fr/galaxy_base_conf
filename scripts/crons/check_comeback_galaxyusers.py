"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
Check deleted galaxyusers who are come back in the ldap, set permissions to their libraries,
create and set permissions to their links and outputs directories and sent an email to admins
"""
import os
import sys
import argparse
from bioblend import galaxy
from bioblend.galaxyclient import ConnectionError
import ldap3
from lib_cron import sendmail, link_permissions, output_permissions, set_library_permissions, library_user_check
from lib_cron import ADMINS_EMAILS, EXCEPTIONS, BASE_DN, ATTRS
sys.path.insert(0, os.path.dirname(__file__))

DUPLICATE_EXCEPTION = ['apashov@pasteur.fr', 'lsiegwal@pasteur.fr', 'jprigent@pasteur.fr']


def init_connection(arguments):
    """
    Set connection
    :param arguments: args dictionnary
    :return: None
    """
    server = ldap3.Server(arguments.ldap_url, use_ssl=True, get_info=ldap3.ALL)
    gi = galaxy.GalaxyInstance(url=arguments.url, key=arguments.key)
    gi.verify = False
    with ldap3.Connection(server, auto_bind=True, check_names=True) as conn:
        check_deleted_users(gi, conn, arguments.base_link, arguments.base_output, arguments.gid, arguments.domain_list)


def check_deleted_users(gi, ldap_conn, base_link, base_output, gid, domain_list):
    """
    Check if deleted users are in the LDAP, set permissions for the library and create
    and set permissions for links and outputs folders
    :param gi: Galaxy instance object
    :param base_link: links directory path
    :param base_output: outputs directory path
    :param ldap_conn: ldap connection object
    :param gid: bioweb group gid
    :param domain_list: galaxy users email domain
    :return: None
    """
    libraries = gi.libraries.get_libraries()
    roles = gi.roles.get_roles()
    message = str()
    try:
        deleted_users = gi.users.get_users(deleted=True)
    except ConnectionError, e:
        sendmail(ADMINS_EMAILS, "##### ERROR ##### during the display API galaxy command : {0}."
                 " CRON: {1}\n".format(e, os.path.basename(__file__)), "Galaxy connection error")
        sys.exit(1)
    for user in deleted_users:
        if not (user['email'] in EXCEPTIONS or user['email'] in DUPLICATE_EXCEPTION):
            user_uid, domain = user['email'].split('@')
            if domain in domain_list:
                ldap_filter = '(& (objectclass=posixAccount) (uid={0}))'.format(user_uid)
                resp = ldap_conn.search(BASE_DN, ldap_filter, attributes=ATTRS)
                if resp:
                    message += "USER : {email}\n\nThis user is in the LDAP Pasteur and is come back into " \
                               "the Galaxy Pasteur: email: {email} - user_uid: {id}\n\n".format(**user)
                    user_library = library_user_check(libraries, user)
                    if user_library:
                        set_library_permissions(gi, user_library, roles, user)
                    else:
                        message += "##### ERROR ##### the user: email - {email} id - {id} has no library with his " \
                                   "email as name. CRON: {0}\n\n".format(os.path.basename(__file__), **user)
                    message += link_permissions(base_link, user, ldap_conn, gid)
                    message += output_permissions(base_output, user, ldap_conn, gid)
    sendmail(ADMINS_EMAILS, message, 'Galaxy: LDAP users come back')


if __name__ == "__main__":
    # Arguments parser
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--url', help='')
    parser.add_argument('--key', help='')
    parser.add_argument('--ldap_url', help='')
    parser.add_argument('--base_link', help='')
    parser.add_argument('--base_output', help='')
    parser.add_argument('--gid', type=int, metavar='N', help='')
    parser.add_argument('--domain_list', nargs='*', help='')
    args = parser.parse_args()
    init_connection(args)
