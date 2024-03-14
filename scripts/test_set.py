#%%
from pathlib import Path
from bressen import read_directory, read_files
from bressen.vlakken import aggregate_peil
from bressen.styles import add_styles_to_geopackage
from bressen.geometries import get_closest_feature, project_point, get_containing_feature
import geopandas as gpd
from shapely.geometry import LineString, Point, MultiLineString
from shapely import ops

DATA_DIR = Path(r"d:\projecten\D2405.waternet.bressen\01.gegevens")

gpkg_out = DATA_DIR / "bressen_test.gpkg"


# %% inlezen

# inlezen peilvakken
gdf = read_directory(DATA_DIR / "04_Peilvlakken")

peil_kolommen = ['IWS_GPGVAS', 'IWS_GPGOND', 'IWS_GPGBOV', 'VAST_PEIL', 'FLEXIBEL_W', 'FLEXIBEL_Z', 'WINTERPEIL', 'ZOMERPEIL']
peilen_gdf = aggregate_peil(gdf, columns=peil_kolommen, method="min", nodata=0)

peilen_gdf.to_file(gpkg_out, layer="peilvlakken", engine="pyogrio")


# inlezen watervlakken
water_gdf = read_directory(DATA_DIR / "05_Watervlakken")
water_gdf.to_file(gpkg_out, layer="watervlakken", engine="pyogrio")

# inlezen bressen
bressen_gdf = gpd.read_file(DATA_DIR.joinpath("03_Doorbraaklocaties", "Bres_Test_060324.shp"))
bressen_gdf.to_file(gpkg_out, layer="bressen", engine="pyogrio")

# inlezen keringen
keringen_gdf = read_files(
    [DATA_DIR.joinpath("01_AGV_Dijktrajecten_Legger", "240122_Export_Output_11_verwerkt.shp"),
     DATA_DIR.joinpath("02_ARK_Kering", "240212_Waterkeringen_Blaeu_ARK.shp")]
     )
keringen_gdf = keringen_gdf.explode(index_parts=False) #MultiLineStrings to singles ivm buffering
keringen_gdf.reset_index(inplace=True)
keringen_gdf.to_file(gpkg_out, layer="keringen", engine="pyogrio")


# %% verwerken bressen

# verwerken bressen
tolerance = 0.1
x1 = 50
x2 = 40
x3 = 200
data = []

for row in bressen_gdf.itertuples():
    # 1. selecteer dichtsbijzijnde kering binnen tolerantie
    kering = get_closest_feature(row, keringen_gdf, max_distance=tolerance)
    if kering is None:
        raise ValueError(f"Geen kering gevonden binnen {tolerance} van bres met fid {row.Index}")
    else:
        offsets = gpd.GeoSeries([kering.geometry.parallel_offset(x1, side=side) for side in ["left", "right"]])
        if (offsets.geom_type == "MultiLineString").any():
            offsets = offsets.geometry.apply(lambda x: ops.linemerge(x) if isinstance(x, MultiLineString) else x)
        
    # 2. bepaal offset_locatie (1) naast watervlak (2) in laagste peilgebied (3) binnen beheergebied

    # haal watervlak op
    watervlak = get_closest_feature(row, water_gdf, max_distance=x1)
    if watervlak is not None: # (1) naast watervlak
        idx = offsets.distance(watervlak.geometry).sort_values(ascending=False).index[0]
        offset_locatie = "naast watervlak"
    else:
        # zoek 1 of meerdere peilvlakken
        offset_points = (project_point(line, row.geometry) for line in offsets)
        peilvlakken = [get_containing_feature(geometry, peilen_gdf) for geometry in offset_points]
        peilen = [i.peil if i is not None else None for i in peilvlakken]
        if all(peilen): # (2) tussen twee peilvlakken, we kiezen laagste peil
            if peilen[0] == peilen[1]:
                print(f"Peilvlak(ken) aan beiden zijden van bres met fid {row.Index} hebben zelfde peil: {peilen[0]} m NAP op afstand {x1}")
                continue
                raise ValueError(f"Peilvlak(ken) aan beiden zijden van bres met fid {row.Index} hebben zelfde peil: {peilen[0]} m NAP op afstand {x1}")
            else:
                idx = peilen.index(min(peilen))
                offset_locatie = "laagste peilvlak"
        elif not any(peilen):
            print(f"Geen peilvlakken aan een zijde van bres met fid {row.Index} afstand {x1}")
            continue
            raise ValueError(f"Geen peilvlakken aan een zijde van bres met fid {row.Index} afstand {x1}")
        else: # (3) we kiezen het peilvlak binnen het beheergebied
            idx = next((idx for idx, i in enumerate(peilen) if i is not None))
            offset_locatie = "binnen beheergebied"

    bres_offset = offsets[idx]  

    #% afleiden bres-polygon
    mid_distance = bres_offset.project(row.geometry)
    min_distance= mid_distance - x3/2
    max_distance= mid_distance + x3/2
    line_start = bres_offset.interpolate(min_distance)
    line_end = bres_offset.interpolate(max_distance)
    distances = (bres_offset.project(Point(i)) for i in bres_offset.coords)
    line_vertices = [bres_offset.interpolate(i) for i in distances if (i > min_distance) and (i < max_distance)]
    bres_line = LineString(([line_start]+ line_vertices + [line_end]))
    bres_poly = bres_line.buffer(x2/2, cap_style="flat")

    #% toevoegen aan data
    row_dict = row._asdict()
    row_dict["geometry"] = bres_poly
    row_dict["offset_locatie"] = offset_locatie
    data += [row_dict]

#%% wegschrijven

# wegschrijven bressen
bresvlakken_gdf = gpd.GeoDataFrame(data, crs=bressen_gdf.crs)
bresvlakken_gdf.drop(columns="Index", inplace=True)
bresvlakken_gdf.to_file(gpkg_out, layer="bresvlakken", engine="pyogrio")

# %% toevoegen styling aan geopackage

# toevoegen styles
add_styles_to_geopackage(gpkg_out)
# %%
