# coding: utf-8
"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
Cron library
"""
from bioblend import galaxy
from bioblend.galaxyclient import ConnectionError
from email.mime.text import MIMEText
import os
import smtplib
import sys
import ldap3

# Mail information
GALAXY_EMAIL = "no-reply.galaxy@pasteur.fr"
ADMINS_EMAILS = "galaxy@pasteur.fr"
# ADMINS_EMAILS = "fmareuil@pasteur.fr"
# LDAP information
BASE_DN = 'dc=corp,dc=pasteur,dc=fr'
ATTRS = ['proxyAddresses']
# List of galaxy user exceptions, old production user and duplicate user
EXCEPTIONS = ['(null)', 'galaxyhimself@pasteur.fr', 'bioweb-prod@pasteur.fr']

welcome_message = """Hello,
Your data library within Galaxy has been activated and administrated, you can start using it.
You can copy data in the directory /pasteur/projets/common/galaxy/links/'yourLogin'@pasteur.fr in order to upload them in the galaxy instance.
An output directory (/pasteur/projets/common/galaxy/outputs/'yourLogin'@pasteur.fr)" was also created for the tool export_data in the tab Send Data.
This message is transmitted automatically by Galaxy, please do not reply to this email. If you have any questions, please contact informatique@pasteur.fr.
Don't forget to activate your account.

Best regards,
The Galaxy team.
--
Centre d'Informatique pour la Biologie


Bonjour,
Votre 'librairie' dans galaxy a été paramétrée, vous pouvez maintenant l'utiliser. Vous pouvez déposer vos données dans pasteur /projets/common/galaxy/links/'yourLogin'@pasteur.fr et les importer dans votre 'librairie' via l'interface galaxy.
Un répertoire de sortie (/pasteur/projets/common/galaxy/outputs/'yourLogin'@pasteur.fr) a aussi été créé pour l'outil export_data dans l'onglet Send Data.
Ce message vous est transmis automatiquement par Galaxy, merci de ne pas y répondre. Pour toute question, veuillez contacter informatique@pasteur.fr.
N'oubliez pas d'activer votre compte.

Cordialement,
L'équipe Galaxy.
--
Centre d'Informatique pour la Biologie
"""


def check_ldap_status(email, ldap, ldap_user, ldap_password):
    """
    Create ldap connection object check email and return resp
    :param email: string user email
    :param ldap: ldap url
    :param ldap_user: ldap user
    :param ldap_password: ldap password
    :return: list
    """
    server = ldap3.Server(ldap, use_ssl=True, get_info=ldap3.ALL)
    with ldap3.Connection(server, auto_bind=True, check_names=True, user=ldap_user, password=ldap_password) as conn:
        ldap_filter = '(&(proxyAddresses=smtp:{0})' \
                      '(objectClass=user)(!(UserAccountControl:1.2.840.113556.1.4.803:=2)))'.format(email)
        resp = conn.search(BASE_DN, ldap_filter, attributes=ATTRS)
        emaillist = []
        if resp:
            for mail in conn.response[0]['attributes']['proxyAddresses']:
                if 'smtp:' in mail.lower():
                    emaillist.append(mail.strip('smtp:').strip('SMTP:'))
        return emaillist


def check_otheraccount(email, emaillist, users):
    """
    Check if a user already have an email/account with pasteur privilege
    :param email: string email current user
    :param emaillist: list emails associated with the user
    :param users: list of galaxy users
    :return: boolean
    """
    for mail in emaillist:
        if email != mail:
            for user in users:
                if user["group_name"] == "pasteur_users" and mail == user["email"]:
                    return True
    return False


def get_users_and_group_users(gi):
    """
    Create dictionnary with user id, user email and user group
    :param gi: galaxy instance object
    :return: dictionnary user, pasteur group id, external group id
    """
    try:
        users = gi.users.get_users(deleted=False)
        users = [{'email': user['email'], 'id': user['id']} for user in users]
        pasteur_group_id = groupid_from_name(gi, "pasteur_users")
        pasteur_users = gi.groups.get_group_users(pasteur_group_id)
        pasteur_users = [{'email': user['email'], 'id': user['id']} for user in pasteur_users]
        external_group_id = groupid_from_name(gi, "external_users")
        external_users = gi.groups.get_group_users(external_group_id)
        external_users = [{'email': user['email'], 'id': user['id']} for user in external_users]
        for user in users:
            if user in pasteur_users:
                user['group_id'] = pasteur_group_id
                user['group_name'] = "pasteur_users"
            elif user in external_users:
                user['group_id'] = external_group_id
                user['group_name'] = "external_users"
            else:
                user['group_id'] = ""
                user['group_name'] = ""

    except ConnectionError, e:
        sendmail(ADMINS_EMAILS, "##### ERROR ##### during the display bioblend galaxy command, connection error : {0}."
                                " CRON: {1}\n".format(e, os.path.basename(__file__)), "Galaxy: user is not in the LDAP")
        sys.exit(1)
    return users, pasteur_group_id, external_group_id


def groupid_from_name(gi, name):
    """
    Return galaxy group id from galaxy group name
    :param gi: Galaxy instance object
    :param name: string group name
    :return: string group id
    """
    groups = gi.groups.get_groups()
    for group in groups:
        if group['name'] == name:
            return group['id']


def sendmail(recipient, msg, subject):
    """
    Create a text/plain message and send the message via our own SMTP server, but don't include the
    envelope header.
    :param recipient: recipient mail string
    :param msg: messages string
    :param subject: mail title
    :return: None
    """
    if msg:
        msg = MIMEText(msg, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = GALAXY_EMAIL
        msg['To'] = recipient
        s = smtplib.SMTP('smtp.pasteur.fr')
        s.sendmail(GALAXY_EMAIL, recipient, msg.as_string())
        s.quit()


def link_permissions(path, user):
    """
    Create link folder
    :param path: links directory path
    :param user: user dictionnary
    :return: error messages
    """
    msg = str()
    try:
        folders_links = os.listdir(path)
    except OSError, e:
        msg += "##### ERROR ##### {0}, {1} path doesn't exist. CRON: {2}\n".format(e, path, os.path.basename(__file__))
        return msg
    if user['email'] not in folders_links:
        path_links = os.path.join(path, user['email'])
        try:
            os.mkdir(path_links)
            msg += "This user has links folder ; user email : {email} - user uid: {id}\n".format(**user)
        except OSError, e:
            msg += "##### ERROR ##### during the creation of the links directory of {0[id]} user id, email - " \
                   "{0[email]}.\n {1} \n CRON: {2}\n".format(user, e, os.path.basename(__file__))
    else:
        msg += "The user {0[email]} already own a directory 'links'\n".format(user)
    return msg


def set_library_folder(gi, user, message, base_link):
    """
    Create Galaxy library and set permission and create link folder
    :param gi: Galaxy instance object
    :param user: dict user
    :param message: string message for mail
    :param base_link: path directory link
    :return: message string for mail
    """
    if gi.libraries.get_libraries(name=user['email'], deleted=False):
        message += "##### ERROR ##### The library: {0[email]} - library id: {0[id]} already exist " \
                   "and is not tagged deleted. CRON {1}\n".format(user, os.path.basename(__file__))
        message += link_permissions(base_link, user)
    elif not gi.libraries.get_libraries(name=user['email'], deleted=True):
        roles = gi.roles.get_roles()
        library_info = gi.libraries.create_library(user['email'],
                                                   description="Library of {0}".format(user['email']))
        message += "Creation of the library of {1[email]} - user id: {1[id]} - " \
                   "library id: {0[id]}\n".format(library_info, user)
        message += set_library_permissions(gi, library_info, roles, user)
        message += link_permissions(base_link, user)
        sendmail(user['email'], welcome_message, "Welcome to (the) Galaxy")
    else:
        message += "##### ERROR ##### The library: {0[email]} - library id: {0[id]} already exist " \
                   "but is tagged deleted. CRON {1}\n".format(user, os.path.basename(__file__))
        message += link_permissions(base_link, user)
    return message


def delete_big_mem_quota_user(gi, user):
    """
    Delete user from bi_user quota
    :param gi: galaxy instance object
    :param user:  information dict of a user
    :return:
    """
    biguser_quota = get_quota_pasteur(gi)
    info_biguser_quota = gi.quotas.show_quota(biguser_quota['id'])
    users_biguser_quota = [i['user']['id'] for i in info_biguser_quota['users']]
    if user['id'] in users_biguser_quota:
        users_biguser_quota.remove(user['id'])
        gi.make_put_request(os.path.join(gi.quotas.url, str(biguser_quota['id'])),
                            {'in_users': users_biguser_quota})


def set_library_permissions(galaxy_instance, lib, roles, user):
    """
    Give permissions to his library for a user
    :param galaxy_instance: bioblend galaxy instance
    :param lib: library dictionnary
    :param roles: list of galaxy roles
    :param user: user dictionnary
    :return: message string for mail
    """
    msg = str()
    user_role = dict()
    library_permissions = galaxy_instance.libraries.get_library_permissions(lib['id'])
    access_library_role_list_id = [idt[1] for idt in library_permissions["access_library_role_list"]]
    add_library_item_role_list_id = [idt[1] for idt in library_permissions["add_library_item_role_list"]]
    manage_library_role_list_id = [idt[1] for idt in library_permissions["manage_library_role_list"]]
    modify_library_role_list_id = [idt[1] for idt in library_permissions["modify_library_role_list"]]
    for role in roles:
        if role['name'] == user['email']:
            user_role = role
    if user_role:
        access_library_role_list_id.append(user_role['id'])
        add_library_item_role_list_id.append(user_role['id'])
        manage_library_role_list_id.append(user_role['id'])
        modify_library_role_list_id.append(user_role['id'])
        galaxy_instance.libraries.set_library_permissions(lib['id'],
                                                          access_in=access_library_role_list_id,
                                                          modify_in=add_library_item_role_list_id,
                                                          add_in=manage_library_role_list_id,
                                                          manage_in=modify_library_role_list_id)
        msg += "This user has now permissions for the library ( name: {0[name]} - id: {0[id]}); user email: " \
               "{1[email]} - user uid: {1[id]}\n".format(lib, user)
    else:
        msg += "##### ERROR ##### the Galaxy user (email {email} - id {id}) has no role. CRON {0}\n"\
            .format(os.path.basename(__file__), **user)
    return msg


def get_quota_pasteur(galaxyinstance):
    """
    Return the Pasteur dictionnary quota
    :param galaxyinstance: object GalaxyInstance
    :return: quota dictionnary
    """
    quotas = galaxyinstance.quotas.get_quotas()
    quota_pasteur = dict()
    for quota in quotas:
        if quota['name'] == 'big_user':
            quota_pasteur = quota
    return quota_pasteur