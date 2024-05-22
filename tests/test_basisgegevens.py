from bressen import BasisGegevens
from bressen.vlakken import aggregate_peil


def test_peilvlakken(peilvlakken):
    # peilkolommen
    peil_kolommen = [
        "IWS_GPGVAS",
        "IWS_GPGOND",
        "IWS_GPGBOV",
        "VAST_PEIL",
        "FLEXIBEL_W",
        "FLEXIBEL_Z",
        "WINTERPEIL",
        "ZOMERPEIL",
    ]
    assert all((i in peilvlakken.columns for i in peil_kolommen))

    peilvlakken.drop(columns="peil", inplace=True)
    assert "peil" not in peilvlakken.columns

    peilvlakken = aggregate_peil(
        peilvlakken, columns=peil_kolommen, method="min", nodata=0
    )

    assert "peil" in peilvlakken.columns

    assert all(peilvlakken.peil.notna())


def test_basisgegevens(keringen, peilvlakken, watervlakken, basisgegevens_gpkg):
    basisgegevens = BasisGegevens(
        keringen=keringen, peilvlakken=peilvlakken, watervlakken=watervlakken
    )

    assert not basisgegevens_gpkg.exists()

    basisgegevens.to_gpkg(basisgegevens_gpkg)

    assert basisgegevens_gpkg.exists()

    basisgegevens = BasisGegevens.from_gpkg(basisgegevens_gpkg)

    assert not basisgegevens.watervlakken.empty
    assert not basisgegevens.keringen.empty
    assert not basisgegevens.peilvlakken.empty
