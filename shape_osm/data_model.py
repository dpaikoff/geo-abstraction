import pdb
import yaml
import argparse
from geoalchemy2 import Geometry
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema
from sqlalchemy import Table, Column, Integer, String, MetaData
from sqlalchemy_utils import database_exists, create_database, drop_database


def create_db(engine):
    print str(engine.url) + ' Exists: ' + str(database_exists(engine.url))

    if not database_exists(engine.url):
        create_database(engine.url)
        print str(engine.url) + ' Exists: ' + str(database_exists(engine.url))


def create_ext(engine, ext_name):
    try:
        engine.execute("CREATE EXTENSION {}".format(ext_name))
        print "EXTENSION: {} enabled".format(ext_name)
    except:
        print "EXTENSION: {} is already enabled".format(ext_name)


def create_schema(engine, schema_name):
    try:
        engine.execute(CreateSchema(schema_name))
        print "SCHEMA: {} created".format(schema_name)
    except:
        print "SCHEMA: {} already exists".format(schema_name)


def parse_config():
    with open('config.yaml', 'r') as mem:
        config = yaml.load(mem)
    return config


def main():
    config = parse_config()
    user = config['user']
    host = config['host']
    port = config['port']
    db = config['db']

    engine = create_engine("postgres://{}@{}:{}/{}".format(user, host, port, db))

    try:
        drop_database(engine.url)
    except:
        pass

    create_db(engine)
    create_ext(engine, 'PostGIS')
    create_ext(engine, 'hstore')
    create_schema(engine, 'staging')
    create_schema(engine, 'shapes')

    metadata = MetaData(schema='staging')
    grid_last_update = Table('grid_last_update', metadata,
                             Column('id', String, primary_key=True),
                             Column('last_update', String)
                            )

    try:
        grid_last_update.create(engine)
        print 'TABLE: staging.grid_last_update created'
    except:
        print 'TABLE: staging.grid_last_update exists'


if __name__ == '__main__':
    main()

