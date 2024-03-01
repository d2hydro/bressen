#%%
import geopandas as gpd
from shapely.geometry import Point, LineString
"""
Aanpak:
1. selecteer dichtsbijzijnde kering bij bres. We negeren even DWKIDENT, blijven datamodel onafhankelijk
2. selecteer dichtsbijzijnde watervlak
3. maak een offset naar polder-zijde (verste van watervlak)
4. knip offset op maximale lengte
5. transformeer offset naar polygon
"""


top10NL_gpkg = r"d:\projecten\D2306.LHM_RIBASIM\02.brongegevens\Basisgegevens\Top10NL\top10nl_Compleet.gpkg"
bressen_shp = r"d:\projecten\D2405.waternet.bressen\01.gegevens\03_Doorbraaklocaties\240122_breslocaties_gelijk_groter_1000.shp"
keringen_shp = r"d:\projecten\D2405.waternet.bressen\01.gegevens\01_AGV_Dijktrajecten_Legger\240122_Export_Output_11_verwerkt.shp"
bressen_gpkg = r"d:\projecten\D2405.waternet.bressen\01.gegevens\bressen.gpkg"

bounds = (115650,469850,117200,470800)
watervlakken_gdf = gpd.read_file(top10NL_gpkg, layer="top10nl_waterdeel_vlak", bbox=bounds, engine="pyogrio", fid_as_index=True)
bressen_gdf = gpd.read_file(bressen_shp, bbox=bounds, engine="pyogrio", fid_as_index=True)
keringen_gdf = gpd.read_file(keringen_shp, bbox=bounds, engine="pyogrio", fid_as_index=True)

# %%
tolerance = 0.1
x1 = 50
x2 = 40
x3 = 200

bressen_gdf = bressen_gdf[~bressen_gdf.index.isin([653])] # deze gaat nog niet goed!
bressen_poly_gdf = bressen_gdf.copy()

for row in bressen_gdf.itertuples():

    # 1. selecteer dichtsbijzijnde kering
    idx = keringen_gdf.sindex.intersection(row.geometry.buffer(tolerance).bounds)
    kering_geometry = keringen_gdf.at[
        keringen_gdf.iloc[idx].distance(row.geometry).sort_values().index[0],
        "geometry"
    ]

    # 2. selecteer dichtsbijzijnde watervlak
    idx = watervlakken_gdf.sindex.intersection(row.geometry.bounds)
    watervlak_geometry = watervlakken_gdf.at[
        watervlakken_gdf.iloc[idx].distance(row.geometry).sort_values().index[0],
        "geometry"
    ]

    # 3. maak een offset naar polder-zijde (verste van watervlak)
    offsets = gpd.GeoSeries([kering_geometry.parallel_offset(x1, side=side) for side in ["left", "right"]])
    bres_offset = offsets[offsets.distance(watervlak_geometry).sort_values(ascending=False).index[0]]

    # 4. knip offset op maximale lengte
    mid_distance = bres_offset.project(row.geometry)
    min_distance= mid_distance - x3/2
    max_distance= mid_distance + x3/2
    line_start = bres_offset.interpolate(min_distance)
    line_end = bres_offset.interpolate(max_distance)
    distances = (bres_offset.project(Point(i)) for i in bres_offset.coords)
    line_vertices = [bres_offset.interpolate(i) for i in distances if (i > min_distance) and (i < max_distance)]
    bres_line = LineString(([line_start]+ line_vertices + [line_end]))

    # 5. transformeer offset naar polygon
    bres_poly = bres_line.buffer(x2/2, cap_style="flat")
    bressen_poly_gdf.loc[row.Index, "geometry"] = bres_poly

bressen_poly_gdf.to_file(bressen_gpkg, engine="pyogrio",)

# %%
