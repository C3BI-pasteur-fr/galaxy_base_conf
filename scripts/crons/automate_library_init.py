# coding: utf-8
"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
library creation, links directory creation, outputs directory creation
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

welcome_message = """Hello,
Your data library within Galaxy has been activated and administrated, you can start using it.
You can copy data in the directory/pasteur/projets/common/galaxy/links/'yourLogin'@pasteur.fr in order to upload them in the galaxy instance.
An output directory (/pasteur/projets/common/galaxy/outputs/'yourLogin'@pasteur.fr)" was also created for the tool export_data in the tab Send Data.
This message is transmitted automatically by Galaxy, please do not reply to this email. If you have any questions, please contact informatique@pasteur.fr.

Best regards,
The Galaxy team.
--
Centre d'Informatique pour la Biologie


Bonjour,
Votre 'librairie' dans galaxy a été paramétrée, vous pouvez maintenant l'utiliser. Vous pouvez déposer vos données dans pasteur/projets/common/galaxy/links/'yourLogin'@pasteur.fr et les importer dans votre 'librairie' via l'interface galaxy.
Un répertoire de sortie (/pasteur/projets/common/galaxy/outputs/'yourLogin'@pasteur.fr) a aussi été créé pour l'outil export_data dans l'onglet Send Data.
Ce message vous est transmis automatiquement par Galaxy, merci de ne pas y répondre. Pour toute question, veuillez contacter informatique@pasteur.fr.

Cordialement,
L'équipe Galaxy.
--
Centre d'Informatique pour la Biologie
"""

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
        create_libraries_folders(gi, conn, arguments.base_link, arguments.base_output, arguments.gid,
                                 arguments.domain_list)


def get_quota_pasteur(galaxyinstance):
    """
    Return the Pasteur dictionnary quota
    :param galaxyinstance: object GalaxyInstance
    :return: quota dictionnary
    """
    quotas = galaxyinstance.quotas.get_quotas()
    quota_pasteur = dict()
    for quota in quotas:
        if quota['name'] == 'Pasteur':
            quota_pasteur = quota
    return quota_pasteur


def create_libraries_folders(gi, ldap_conn, base_link, base_output, gid, domain_list):
    """
    Check the new galaxy users, attribute their quotas, create and set their library permissions,
    create links and outputs folders and set permissions
    :param gi: Galaxy instance object
    :param base_link: links directory path
    :param base_output: outputs directory path
    :param ldap_conn: ldap connection object
    :param gid: group gid
    :param domain_list: galaxy users email domain
    :return: None
    """
    try:
        users = gi.users.get_users(deleted=False)
    except ConnectionError, e:
        sendmail(ADMINS_EMAILS, "ERROR during the display API galaxy command : {0}. CRON {1}"
                 .format(e, os.path.basename(__file__)), "Galaxy connection error")
        sys.exit(1)
    libraries = gi.libraries.get_libraries()
    roles = gi.roles.get_roles()
    for user in users:
        if not user['email'] in EXCEPTIONS:
            user_uid, domain = user['email'].split('@')
            if domain in domain_list:
                message = str()
                ldap_filter = '(& (objectclass=posixAccount) (uid={0}))'.format(user_uid)
                resp = ldap_conn.search(BASE_DN, ldap_filter, attributes=ATTRS)
                if resp:
                    user_library = library_user_check(libraries, user)
                    # if not user library we consider that the user is new because show_user doesn't give create_time
                    # information
                    if not user_library:
                        pasteur_quota = get_quota_pasteur(gi)
                        info_pasteur_quota = gi.quotas.show_quota(pasteur_quota['id'])
                        users_pasteur_quota = [i['user']['id'] for i in info_pasteur_quota['users']]
                        users_pasteur_quota.append(user['id'])
                        gi.make_put_request(os.path.join(gi.quotas.url, str(pasteur_quota['id'])),
                                            {'in_users': users_pasteur_quota})
                        user_name = user['email'].split('@')[0]
                        library_info = gi.libraries.create_library(user['email'],
                                                                   description="Library of {0}".format(user_name))
                        message += "Creation of the library of {1[email]} - user id: {1[id]} - " \
                                   "library id: {0[id]}\n".format(library_info, user)
                        message += set_library_permissions(gi, library_info, roles, user)
                        message += link_permissions(base_link, user, ldap_conn, gid)
                        message += output_permissions(base_output, user, ldap_conn, gid)
                        sendmail(user['email'], welcome_message, "Welcome to (the) Galaxy")
                        sendmail(ADMINS_EMAILS, message, "Galaxy library creation")
                    elif user_library['deleted']:
                        message += "##### ERROR ##### The library: {1[email]} - library id: {0[id]} already exist " \
                                   "but is tagged deleted. CRON {2}\n".format(user_library, user,
                                                                              os.path.basename(__file__))
                        message += link_permissions(base_link, user, ldap_conn, gid)
                        message += output_permissions(base_output, user, ldap_conn, gid)
                        sendmail(ADMINS_EMAILS, message, "Galaxy library creation")


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
