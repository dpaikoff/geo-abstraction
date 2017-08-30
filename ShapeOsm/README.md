# ShapeOsm 

Is a workflow that creates a .01 x .01 degree cell size vector grid that intersects a given polygon shape. Then each cell's bounding box is used to download osm data using the overpass rest api. Finally, the data is loaded into postgres.

**Dependencies:**

Postgres with PostGIS installed

For testing the [Postgres.app](https://postgresapp.com) was used. It comes prepackaged with PostGIS.

Need to add psql to PATH
	
	export PATH=/Applications/Postgres.app/Contents/Versions/9.6/bin:$PATH

In order to load osm data to postgres the osm2pgsql tool is used. On osx use brew to install.
	
	brew install osm2pgsql

For loading vector data into postgres the shp2pgsql is used. This is included in the Postgres.app.


Example command for loading [Census zipcode polygons](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2016&layergroup=ZIP+Code+Tabulation+Areas):

	shp2pgsql -s 4269 -g geom -I -W "LATIN1" tl_2016_us_zcta510.shp shapes.tl_2016_us_zcta510 | psql -h localhost -U postgres -p 5432 -d geo_abstraction

Setup python environment:

	virtural venv
	source venv/bin/activate
	pip install -r requirements.txt

Example config:
	
	host: localhost
	port: 5432
	db: geo_abstraction
	user: postgres
	
	shape: shapes.tl_2016_us_zcta510
	where: b.geoid10 = '95618'
	out_folder: /Users/dmp/Desktop/test
	table_prefix: zip_95618
	grid_cell_size: .01

Setup database:

	python data_model.py

Finally run:

	python shape_osm.py
