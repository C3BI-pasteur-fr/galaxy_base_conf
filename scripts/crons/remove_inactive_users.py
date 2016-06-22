"""
Created on Feb. 19, 2016

@authors: Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: galaxy_prod_conf
@githuborganization: C3BI
"""
import ConfigParser
import argparse
import datetime
from lib_cron import sendmail
from sqlalchemy import create_engine, select, MetaData
from sqlalchemy.ext.automap import automap_base
from lib_cron import ADMINS_EMAILS

def map_database(connection):
    """
    Return the mapped classes and the engine from a given database
    :param connection: database connection information
    :return: mapped classes , engine
    """
    eng = create_engine(connection)
    metadata = MetaData()
    metadata.reflect(eng)
    base = automap_base(metadata=metadata)
    base.prepare()
    return base.classes, eng


def list_inactive_users(datab, eng):
    """
    Send a mail with informations about Galaxy, Total users, numbers of actives users last year, numbers of inactives
    users last year, number of not Pasteur users and inactive and the list of these users
    :param datab: Mapped classes
    :param eng: engine
    :return: None
    """
    now = datetime.datetime.now()
    oneyearago = datetime.date(now.year-1, now.month, now.day)
    users_actif_last_year = []
    users = []
    user, session = datab.galaxy_user, datab.galaxy_session
    sele = select([user.email])\
        .where(user.deleted == False)\
        .where(user.id == session.user_id)\
        .where(session.update_time > oneyearago)\
        .group_by(user.email)
    with eng.connect() as conn:
        result = conn.execute(sele)
        for row in result:
            users_actif_last_year.append(row[0])
    sele = select([user.email])\
        .where(user.deleted == False)
    with eng.connect() as conn:
        result = conn.execute(sele)
        for row in result:
            users.append(row[0])
    all_users_inactif = set(users) - set(users_actif_last_year)
    extern_users_inactif = []
    for user in all_users_inactif:
        if '@pasteur.fr' not in user:
            extern_users_inactif.append(user)
    message = "Total users: {0}\n" \
              "Actives users last year: {1}\n" \
              "Inactives users last year: {2}\n{3}\n" \
              "Not Pasteur and inactives users last year {4}\n{5}\n".format(len(users), len(users_actif_last_year),
                                                                            len(all_users_inactif),
                                                                            " ".join(all_users_inactif),
                                                                            len(extern_users_inactif),
                                                                            " ".join(extern_users_inactif))
    sendmail(ADMINS_EMAILS, message, "Galaxy Pasteur inactive report")

    return


def config_parsing(configfile):
    """
    Parse galaxy config file and return database connection  and engine
    :param configfile: str
    :return: database, engine
    """
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    db_connection = config.get('app:main', 'database_connection')
    db, eng = map_database(db_connection)
    return db, eng


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--configfile", help="config file of galaxy")
    args = parser.parse_args()
    database, engine = config_parsing(args.configfile)
    list_inactive_users(database, engine)
