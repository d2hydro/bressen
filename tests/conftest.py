# %%
from pathlib import Path

import geopandas as gpd
import pytest

from bressen import BasisGegevens

DATA_DIR = Path(__file__).parent.joinpath("data")
BASISGEGEVENS_GPKG = DATA_DIR / "basisgegevens.gpkg"
BRESSEN_GPKG = DATA_DIR / "bressen" / "bressen.gpkg"


@pytest.fixture
def keringen() -> gpd.GeoDataFrame:
    keringen = gpd.read_file(BASISGEGEVENS_GPKG, layer="keringen", engine="pyogrio")
    return keringen


@pytest.fixture
def watervlakken() -> gpd.GeoDataFrame:
    return gpd.read_file(BASISGEGEVENS_GPKG, layer="watervlakken", engine="pyogrio")


@pytest.fixture
def peilvlakken() -> gpd.GeoDataFrame:
    return gpd.read_file(BASISGEGEVENS_GPKG, layer="peilvlakken", engine="pyogrio")


@pytest.fixture
def bressen_gdf() -> gpd.GeoDataFrame:
    return gpd.read_file(BRESSEN_GPKG, layer="bressen", engine="pyogrio")


@pytest.fixture
def bressen_dir() -> Path:
    return DATA_DIR / "bressen"


@pytest.fixture
def basisgegevens_gpkg(tmp_path) -> Path:
    return tmp_path / "basisgegevens.gpkg"


@pytest.fixture
def bressen_gpkg(tmp_path) -> Path:
    return tmp_path / "bressen.gpkg"


@pytest.fixture
def basisgegevens(keringen, peilvlakken, watervlakken) -> BasisGegevens:
    return BasisGegevens(
        keringen=keringen, peilvlakken=peilvlakken, watervlakken=watervlakken
    )
