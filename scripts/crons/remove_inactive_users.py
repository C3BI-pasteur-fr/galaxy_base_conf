"""
Created on Feb. 19, 2016

@authors: Fabien Mareuil, Olivia Doppelt-Azeroual, Institut Pasteur, Paris
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


def period_check(now, timeperiod):
    """
    :param now:
    :param timeperiod:
    :return: datetime object
    """
    mod = (int(timeperiod)%12)
    div = (int(timeperiod)/12)
    if int(timeperiod) < int(now.month):
        return datetime.date(now.year, int(now.month) - mod, now.day)
    else:
        return datetime.date(now.year - div, now.month - mod, now.day)


def list_inactive_users(datab, eng, timeperiod):
    """
    Send a mail with informations about Galaxy, Total users, numbers of actives users last year, numbers of inactives
    users last year, number of not Pasteur users and inactive and the list of these users
    :param datab: Mapped classes
    :param eng: engine
    :return: None
    """
    now = datetime.\
        datetime.now()
    time = period_check(now, timeperiod)
    active_users_for_timeperiod = []
    users = []
    group_association = {}
    user, session, group_assoc, group = datab.galaxy_user, datab.galaxy_session, datab.user_group_association, \
                                        datab.galaxy_group
    sele = select([user.email])\
        .where(user.deleted == False)\
        .where(user.id == session.user_id)\
        .where(session.update_time > time)\
        .group_by(user.email)
    with eng.connect() as conn:
        result = conn.execute(sele)
        for row in result:
            active_users_for_timeperiod.append(row[0])
    sele = select([user.email])\
        .where(user.deleted == False)
    with eng.connect() as conn:
        result = conn.execute(sele)
        for row in result:
            users.append(row[0])
    sele = select([group.name, user.email])\
        .where(group.id == group_assoc.group_id)\
        .where(user.id == group_assoc.user_id)
    with eng.connect() as conn:
        result = conn.execute(sele)
        for row in result:
            if row[0] in group_association:
                group_association[row[0]].append(row[1])
            else:
                group_association[row[0]] = [row[1]]

    all_inactive_users = set(users) - set(active_users_for_timeperiod)
    external_inactive_users = []
    for user in all_inactive_users:
        if user not in group_association["pasteur_users"]:
            external_inactive_users.append(user)
    message = "Total users: {0}\n" \
              "Actives users in the last {1} month(s):  {7}\n {3} \n" \
              "Inactives users in the last {1} month(s): {2}\n{4}\n" \
              "Not Pasteur and inactives users in the last {1} month(s): {5}\n{6}\n".format(len(users), timeperiod,
                                                                            len(all_inactive_users), " ".join(active_users_for_timeperiod),

                                                                            " ".join(all_inactive_users),
                                                                            len(external_inactive_users),
                                                                            " ".join(external_inactive_users), len(active_users_for_timeperiod))
    sendmail(ADMINS_EMAILS, message, "Galaxy Pasteur inactive users Report")

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
    parser.add_argument("--timeperiod", help="time in month to define inactive user")
    args = parser.parse_args()
    database, engine = config_parsing(args.configfile)
    list_inactive_users(database, engine, args.timeperiod)
