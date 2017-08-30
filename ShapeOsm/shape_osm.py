import os
import pdb
import glob
import yaml
import argparse
import requests
import pandas as pd
import psycopg2 as pg
from datetime import datetime
from geoalchemy2 import Geometry
from sqlalchemy.sql import select
from subprocess import Popen, PIPE
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, Float, String, MetaData


class OsmShapeGrid(object):

    def __init__(self):
        config = parse_config()
        self.host = config['host']
        self.port = config['port']
        self.db = config['db']
        self.user = config['user']
        self.shape = config['shape']
        self.where = config['where']
        self.table_prefix = config['table_prefix']
        self.grid_cell_size = config['grid_cell_size']
        self.out_folder = config['out_folder']
        db_url = 'postgres://{}@{}:{}/{}'.format(self.user, self.host, self.port, self.db)
        self.engine = create_engine(db_url, echo=True)
        self.conn = self.engine.connect()

    def create_grid_add_osm(self):
        schema = 'staging'
        datestamp = datetime.now().strftime('%Y%m%d_%H%M')
        table = "temp_grid_{}".format(datestamp)
        metadata = MetaData(schema=schema)
        temp_grid = Table(table, metadata,
                          Column('grid_id', String, primary_key=True),
                          Column('left', Float),
                          Column('top', Float),
                          Column('right', Float),
                          Column('bottom', Float),
                          Column('geom', Geometry(geometry_type='POLYGON'))
                         )
        temp_grid.create(self.engine)

        bbox = find_bbox(self.conn, self.shape, self.where)
        rows = create_bbox_grid(self.grid_cell_size, bbox)

        self.conn.execute(temp_grid.insert(), rows)
        set_table_srid(self.conn, schema, table, 'geom', 4269)
        in_grid = schema + '.' + table
        out_grid = schema + '.' + table + '_intersect'
        intersect_grid_with_shape(self.conn, in_grid, out_grid, self.shape, self.where)
        df = pd.read_sql("SELECT * FROM {}".format(out_grid), self.conn)
        df.drop('geom', axis=1, inplace=True)
        self.download_osm(df, self.out_folder)

    def download_osm(self, df, out_folder):
        for i, row in df.iterrows():
            bbox = "[bbox={},{},{},{}]".format(row['left'],
                                               row['top'],
                                               row['right'],
                                               row['bottom']
                                              )
            url = "http://www.overpass-api.de/api/xapi?*{}[@meta]".format(bbox)
            print "downloading {}".format(bbox)
            r = requests.get(url)
            out_file = os.path.join(out_folder, row['grid_id'] + '.osm')
            with open(out_file, 'wb') as mem:
                mem.write(r.content)
            if i == 0:
                self.add_osm(out_file, '-c')
            else:
                self.add_osm(out_file, '-a')

    def add_osm(self, osm_file, create_append):
        cmd = ['osm2pgsql',
               '-d', self.db,
               '-H', self.host,
               '-U', self.user,
               '-P', str(self.port),
               '--hstore',
               '--slim',
               '--cache', str(20000),
               '-p', 'shape_{}'.format(self.table_prefix),
               create_append,
               osm_file
              ]
        p = Popen(cmd, stdout=PIPE)


def set_table_srid(conn, schema, table, geom_col, srid):
    conn.execute("ALTER TABLE {}.{} \
                  ALTER COLUMN {} TYPE geometry(Polygon, {}) \
                  USING ST_SetSRID({}, {}); \
                 ".format(schema, table, geom_col, srid, geom_col, srid)
                )


def parse_row_bbox(row):
    bbox = {}
    replace_chars = row.replace('BOX', '').replace('(', '').replace(')', '').replace(',', ' ')
    split_values = replace_chars.split(' ')
    bbox['xmin'] = float(split_values[0])
    bbox['ymin'] = float(split_values[1])
    bbox['xmax'] = float(split_values[2])
    bbox['ymax'] = float(split_values[3])
    return bbox


# def find_bbox(conn, schema, table, where):
def find_bbox(conn, shape, where):
    sql = "SELECT ST_Extent(b.geom) FROM {} b WHERE {};".format(shape, where)
    result = conn.execute(sql)
    for row in result:
        bbox = parse_row_bbox(row[0])
        break
    return bbox


def intersect_grid_with_shape(conn, in_grid, out_grid, shape, where):
    sql = """
             CREATE TABLE {} AS
             (
             SELECT a.grid_id, a.left, a.top, a.right, a.bottom, a.geom
             FROM
             {} a,
             {} b
             WHERE ST_Intersects(a.geom, b.geom)
             AND
             {}
             );
          """.format(out_grid, in_grid, shape, where)
    conn.execute(sql)


def create_bbox_grid(degrees, bbox):
    xmin = bbox['xmin']
    ymin = bbox['ymin']
    xmax = bbox['xmax']
    ymax = bbox['ymax']

    xmin = round(xmin, 2)
    xmax = round(xmax, 2)
    ymin = round(ymin, 2)
    ymax = round(ymax, 2)

    x_diff = round(abs(xmin) - abs(xmax), 2)
    y_diff = round(abs(ymax) - abs(ymin), 2)

    x_diff = int(x_diff/degrees)
    y_diff = int(y_diff/degrees)

    rows = []
    ymin_original = ymin
    for x_pos in range(x_diff):
        ymin = ymin_original
        xmin_start = round(xmin, 2)
        xmin += degrees
        xmin = round(xmin, 2)
        for y_pos in range(y_diff):
            ymin_start = round(ymin, 2)
            ymin += degrees
            ymin = round(ymin, 2)
            grid_id = ''
            grid_id += str(xmin_start) + '_'
            grid_id += str(ymin_start) + '_'
            grid_id += str(xmin) + '_'
            grid_id += str(ymin)
            geom = "POLYGON(({} {}, \
                             {} {}, \
                             {} {}, \
                             {} {}, \
                             {} {}  \
                           ))".format(xmin_start,
                                      ymin_start,
                                      xmin,
                                      ymin_start,
                                      xmin,
                                      ymin,
                                      xmin_start,
                                      ymin,
                                      xmin_start,
                                      ymin_start
                                     )

            row = {
                   'grid_id': grid_id,
                   'left': xmin_start,
                   'top': ymin_start,
                   'right': xmin,
                   'bottom': ymin,
                   'geom': geom
                  }
            print row
            rows.append(row)

    return rows


def parse_config():
    with open('config.yaml', 'r') as mem:
        config = yaml.load(mem)
    return config


if __name__ == '__main__':
    osg = OsmShapeGrid()
    osg.create_grid_add_osm()

