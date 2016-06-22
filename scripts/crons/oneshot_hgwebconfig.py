"""
Created on Jan. 30, 2015

@authors: Fabien Mareuil, Institut Pasteur, Paris
@contacts: fabien.mareuil@pasteur.fr
@project: bioweb_galaxy
@githuborganization: bioweb
"""
import ConfigParser
import argparse
from sqlalchemy import create_engine, select, MetaData
from sqlalchemy.ext.automap import automap_base


def map_database(connection):
    """
        Database mapping
    """
    eng = create_engine(connection)
    metadata = MetaData()
    metadata.reflect(eng)
    base = automap_base(metadata=metadata)
    base.prepare()
    return base.classes, eng


def list_inactive_users(datab, eng):
    """
        build a list of tools in galaxy
    """
    repos = []
    galaxy_user, repository = datab.galaxy_user, datab.repository
    sele = select([repository.id, repository.name, galaxy_user.username]).where(repository.user_id == galaxy_user.id)
    with eng.connect() as conn:
        result = conn.execute(sele)
        for row in result:
            print "repos/%s/%s = database/community_files/000/repo_%s" % (row[2],row[1],row[0])
        
    return


def config_parsing(configfile):
    """
        Parse the config file
    """
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    db_connection = config.get('app:main', 'database_connection')
    return db_connection


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--configfile", help="config file of galaxy")
    args = parser.parse_args()

    database_connection = config_parsing(args.configfile)
    database, engine = map_database(database_connection)
    list_inactive_users(database, engine)
