"""
Created on Jun. 08, 2016

@authors: Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
"""

import argparse
import ldap3
from crons.remove_inactive_users import config_parsing
from sqlalchemy import select, update

BASE_DN = 'ou=personnes,ou=utilisateurs,dc=pasteur,dc=fr'
ATTRS = ['uid', 'mail']


def externtointern(datab, eng):
    """
    :param datab:
    :param eng:
    :return:
    """
    user = datab.galaxy_user
    stmt = update(user).values(external=False)
    with eng.connect() as conn:
        conn.execute(stmt)
    return

def ldapresult(user_login, ldapurl):
    """
    :param user_login:
    :param ldapurl:
    :return:
    """
    if '@' in user_login:
        user_login = user_login.split('@')[0]
    ldap_filter = '(uid={0})'.format(user_login)
    server = ldap3.Server(ldapurl, use_ssl=True, get_info=ldap3.ALL)
    with ldap3.Connection(server, auto_bind=True, check_names=True) as conn:
        conn.search(BASE_DN, ldap_filter, attributes=ATTRS)
        resp = conn.response
        if len(resp) == 1:
            return resp[0]['attributes']
        else:
            return None

def up_email(datab, eng, ldapurl):
    """
    :param datab:
    :param eng:
    :param ldapurl:
    :return:
    """
    user = datab.galaxy_user
    library = datab.library
    sele = select([user.username])
    selelib = select([library.name])
    with eng.connect() as conn:
        result = conn.execute(sele)
        resultlib = conn.execute(selelib)
    for line in resultlib:
        userlib_info = ldapresult(line[0], ldapurl)
        if userlib_info:
            stmtlib = update(library).where(library.name=='{0}@pasteur.fr'.format(userlib_info['uid'][0])).values(name=userlib_info['mail'][0])
            with eng.connect() as conn:
                conn.execute(stmtlib)
    for row in result:
        user_info = ldapresult(row[0], ldapurl)
        if user_info:
            stmt = update(user).where(user.username==user_info['uid'][0]).values(email=user_info['mail'][0])
            with eng.connect() as conn:
                conn.execute(stmt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--configfile", help="config file of galaxy")
    parser.add_argument('--ldap_url', help='')
    args = parser.parse_args()
    database, engine = config_parsing(args.configfile)
    externtointern(database, engine)
    up_email(database, engine, args.ldap_url)
