# geo-abstraction

This is a collection of tools and scripts that allow for manipulation of OSM data.

### [ShapeOsm](https://github.com)

Is a workflow that creates a .01 x .01 degree cell size vector grid that intersects a given polygon shape. Then each cell's bounding box is used to download osm data using the overpass rest api. Finally, the data is loaded into postgres.
