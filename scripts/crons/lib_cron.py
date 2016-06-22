"""
Created on Mars. 04, 2016

@authors: Mathieu Valade, Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
Cron library
"""
from email.mime.text import MIMEText
import os
import smtplib

# Mail information
GALAXY_EMAIL = "no-reply.galaxy@pasteur.fr"
ADMINS_EMAILS = "galaxy@pasteur.fr"
# LDAP information
BASE_DN = 'ou=personnes,ou=utilisateurs,dc=pasteur,dc=fr'
ATTRS = ['gidNumber', 'uidNumber']
# List of galaxy user exceptions, old production user and duplicate user
EXCEPTIONS = ['(null)', 'galaxyhimself@pasteur.fr', 'bioweb-prod@pasteur.fr']


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


def link_permissions(path, user, connection, gid):
    """
    Change the owner and group id of links folder to the numeric uid and gid of the galaxy user
    :param path: links directory path
    :param user: user dictionnary
    :param connection: ldap connection
    :param gid: bioweb group gid
    :return: error messages
    """
    msg = str()
    try:
        folder_links = os.listdir(path)
    except OSError, e:
        msg += "##### ERROR ##### {0}, {1} path doesn't exist. CRON: {2}\n".format(e, path, os.path.basename(__file__))
        return msg
    if user['email'] not in folder_links:
        path_links = os.path.join(path, user['email'])
        try:
            os.mkdir(path_links, 02750)
            user_uid = connection.response[0]['attributes']['uidNumber']
            os.chown(path_links, user_uid, gid)
            msg += "This user has links folder and permissions ; user email : {email} - user uid: {id}\n".format(**user)
        except OSError, e:
            msg += "##### ERROR ##### during the creation of the links directory of {0[id]} user id, email - " \
                   "{0[email]}.\n {1} \n CRON: {2}\n".format(user, e, os.path.basename(__file__))
    else:
        msg += "The user {0[email]} already own a directory 'links'\n".format(user)
    return msg


def output_permissions(path, user, connection, gid):
    """
    Change the owner and group id of outputs folder to the numeric uid and gid of the galaxy user
    :param path: outputs directory path
    :param user: user dictionnary
    :param connection: ldap connection
    :param gid: bioweb group gid
    :return: error messages
    """
    msg = str()
    try:
        folder_outputs = os.listdir(path)
    except OSError, e:
        msg += "##### ERROR ##### {0}, {1} path doesn't exist. CRON: {2}\n".format(e, path, os.path.basename(__file__))
        return msg
    if user['email'] not in folder_outputs:
        path_outputs = os.path.join(path, user['email'])
        try:
            os.umask(0)
            os.mkdir(path_outputs, 02770)
            user_uid = connection.response[0]['attributes']['uidNumber']
            os.chown(path_outputs, user_uid, gid)
            msg += "This user has outputs folder and permissions ; user email :{0} - user uid: {1}\n"\
                .format(user['email'], user['id'])
        except OSError, e:
            msg += "##### ERROR ##### during the creation of the outputs directory of {0[email]} user.\n {1} \n " \
                   "CRON: {2}\n".format(user, e, os.path.basename(__file__))
    else:
        msg += "The user {0[email]} already own a directory 'outputs'\n".format(user)
    return msg


def library_user_check(libraries_list, user):
    """
    Search a library when the library name == user email
    :param libraries_list: list of galaxy libraries
    :param user: information dict of a user
    :return: library dict
    """
    user_library = dict()
    for lib in libraries_list:
        if lib['name'] == user['email']:
            user_library = lib
            # stop if find a library not deleted
            if not user_library['deleted']:
                break
    return user_library


def set_library_permissions(galaxy_instance, lib, roles, user):
    """
    Give permissions to his library for a user
    :param galaxy_instance: bioblend galaxy instance
    :param lib: library dictionnary
    :param roles: list of galaxy roles
    :param user: user dictionnary
    :return: None
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
