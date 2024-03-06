#%%
from pathlib import Path
from bressen import read_directory
from bressen.vlakken import aggregate_peil
from bressen.styles import add_styles_to_geopackage

DATA_DIR = Path(r"d:\projecten\D2405.waternet.bressen\01.gegevens")


gpkg_out = DATA_DIR / "resultaat.gpkg"


# %% vlakken

# inlezen peilvakken
gdf = read_directory(DATA_DIR / "04_Peilvlakken")

peilen = ['IWS_GPGVAS', 'IWS_GPGOND', 'IWS_GPGBOV', 'VAST_PEIL', 'FLEXIBEL_W', 'FLEXIBEL_Z', 'WINTERPEIL', 'ZOMERPEIL']
gdf = aggregate_peil(gdf, columns=peilen, method="min", nodata=0)

gdf.to_file(gpkg_out, layer="peilvlakken")
add_styles_to_geopackage(gpkg_out)

# inlezen watervlakken
gdf = read_directory(DATA_DIR / "05_Watervlakken")
gdf.to_file(gpkg_out, layer="watervlakken")
