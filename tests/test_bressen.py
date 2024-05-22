from bressen import Bressen


def test_bressen(basisgegevens, bressen_gdf, bressen_gpkg):
    bressen = Bressen.from_gdf(bressen_gdf, basisgegevens)
    bressen.bereken_vlakken(offset=25, lengte=100, breedte=25)

    gdf = bressen.to_gdf()
    assert len(gdf) == len(bressen_gdf)

    assert not bressen_gpkg.exists()
    bressen.to_gpkg(bressen_gpkg)

    assert bressen_gpkg.exists()
