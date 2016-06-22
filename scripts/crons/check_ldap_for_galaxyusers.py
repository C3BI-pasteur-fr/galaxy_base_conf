"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
Check non deleted galaxyusers who aren't in the LDAP and sent an email to admins
"""
import os
import sys
from bioblend import galaxy
from bioblend.galaxyclient import ConnectionError
import ldap3
import argparse
from lib_cron import sendmail
from lib_cron import ADMINS_EMAILS, EXCEPTIONS, BASE_DN, ATTRS
sys.path.insert(0, os.path.dirname(__file__))


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
        catch_deleted_users(gi, conn, arguments.domain_list)


def catch_deleted_users(gi, ldap_conn, domain_list):
    """
    Check if galaxy users are in the LDAP
    :param gi: Galaxy instance object
    :param ldap_conn: ldap connection object
    :param domain_list: galaxy users email domain
    :return: None
    """
    try:
        users = gi.users.get_users(deleted=False)
    except ConnectionError, e:
        sendmail(ADMINS_EMAILS, "##### ERROR ##### during the display bioblend galaxy command, connection error : {0}."
                                " CRON: {1}\n".format(e, os.path.basename(__file__)), "Galaxy: user is not in the LDAP")
        sys.exit(1)
    message = str()
    for user in users:
        if not user['email'] in EXCEPTIONS:
            user_uid, domain = user['email'].split('@')
            ldap_filter = '(& (objectclass=posixAccount) (uid={0}))'.format(user_uid)
            resp = ldap_conn.search(BASE_DN, ldap_filter, attributes=ATTRS)
            if domain in domain_list and not resp:
                message += "USER {email}\nThe user is not in the LDAP; email: {email} - user_uid: {id}\n\n"\
                               .format(**user)
    sendmail(ADMINS_EMAILS, message, 'Galaxy: user is not in the LDAP')


if __name__ == "__main__":
    # Arguments parser
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--url', help='')
    parser.add_argument('--key', help='')
    parser.add_argument('--ldap_url', help='')
    parser.add_argument('--domain_list', nargs='*', help='')
    args = parser.parse_args()
    init_connection(args)
