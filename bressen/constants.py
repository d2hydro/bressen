import fiona

try:
    VECTOR_DRIVER_EXTENSIONS = fiona.drvsupport.vector_driver_extensions()
except AttributeError | ModuleNotFoundError:
    VECTOR_DRIVER_EXTENSIONS = {
        "dxf": "DXF",
        "csv": "CSV",
        "tsv": "CSV",
        "psv": "CSV",
        "gdb": "OpenFileGDB",
        "shp": "ESRI Shapefile",
        "dbf": "ESRI Shapefile",
        "shz": "ESRI Shapefile",
        "shp.zip": "ESRI Shapefile",
        "fgb": "FlatGeobuf",
        "json": "GeoJSON",
        "geojson": "GeoJSON",
        "geojsonl": "GeoJSONSeq",
        "geojsons": "GeoJSONSeq",
        "gpkg": "GPKG",
        "gpkg.zip": "GPKG",
        "gml": "GML",
        "xml": "GML",
        "gmt": "OGR_GMT",
        "gpx": "GPX",
        "tab": "MapInfo File",
        "mif": "MapInfo File",
        "mid": "MapInfo File",
        "dgn": "DGN",
        "pix": "PCIDSK",
        "sqlite": "SQLite",
        "db": "SQLite",
    }

VECTOR_DRIVER_EXTENSIONS.pop("xml")
VECTOR_DRIVER_EXTENSIONS.pop("dbf")
VECTOR_DRIVER_EXTENSIONS.pop("shz")
