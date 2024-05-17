from dataclasses import dataclass, field
from typing import Optional

from pyproj.crs.crs import CRS
from shapely.geometry import LineString, Point, Polygon

from bressen.basisgegevens import BasisGegevens
from bressen.geometries import get_closest_feature, get_containing_feature, get_offsets, project_point
from bressen.kering import KeringNotFoundError, get_kering_geometry


@dataclass
class Bres:
    fid: int
    punt: Point
    polygoon: Optional[Polygon] = None
    offset: Optional[float] = None
    offset_locatie: Optional[str] = None
    breedte: Optional[float] = None
    lengte: Optional[float] = None
    eigenschappen: Optional[dict] = dict

    @classmethod
    def from_row(cls, row):
        fid = row.Index
        punt = row.geometry
        eigenschappen = row._asdict()
        eigenschappen.pop("Index")
        eigenschappen.pop("geometry")
        return cls(fid=fid, punt=punt, eigenschappen=eigenschappen)

    def bereken_polygoon(
        self, offset: float, lengte: float, breedte: float, basisgegevens: BasisGegevens, tolerantie=0.01
    ):
        self.offset = offset
        self.lengte = lengte
        self.breedte = breedte

        # 1. selecteer dichtsbijzijnde kering binnen tolerantie
        try:
            kering_geometry = get_kering_geometry(
                self.punt,
                keringen=basisgegevens.keringen,
                min_length=self.lengte,
                max_distance=tolerantie,
                max_line_extends=1,
            )
        except KeringNotFoundError:
            raise KeringNotFoundError(
                f"geen kering gevonden voor fid {self.fid} binnen gespecificeerde tolerantie {tolerantie}"
            )

        # 2. bepaal offset_locatie (1) naast watervlak (2) in laagste peilgebied (3) binnen beheergebied

        # haal watervlak op
        watervlak = get_closest_feature(self.punt, basisgegevens.watervlakken, max_distance=self.offset)
        if watervlak is not None:  # (1) naast watervlak
            offset_distance = max(min(offset, watervlak.geometry.distance(self.punt)), tolerantie)
            offsets = get_offsets(kering_geometry, offset_distance)
            offset_points = offsets.apply(lambda x: project_point(x, self.punt))
            idx = offset_points.distance(watervlak.geometry).sort_values(ascending=False).index[0]
            self.offset_locatie = "naast watervlak"
            if offset_distance != self.offset:
                offsets = get_offsets(kering_geometry, self.offset, check_emtpy_lines=False)
        else:
            # zoek 1 of meerdere peilvlakken
            offsets = get_offsets(kering_geometry, self.offset)
            offset_points = (project_point(line, self.punt) for line in offsets)
            peilvlakken = [get_containing_feature(geometry, basisgegevens.peilvlakken) for geometry in offset_points]
            peilen = [i.peil if i is not None else None for i in peilvlakken]
            if all(peilen):  # (2) tussen twee peilvlakken, we kiezen laagste peil
                if peilen[0] == peilen[1]:
                    print(
                        f"Peilvlak(ken) aan beiden zijden van bres met fid {self.fid} hebben zelfde peil: {peilen[0]} m NAP op afstand {self.offset}"
                    )
                    return
                else:
                    idx = peilen.index(min(peilen))
                    self.offset_locatie = "laagste peilvlak"
            elif not any(peilen):
                print(f"Geen peilvlakken aan een zijde van bres met fid {self.fid} afstand {self.offset}")
                return
            else:  # (3) we kiezen het peilvlak binnen het beheergebied
                idx = next((idx for idx, i in enumerate(peilen) if i is not None))
                self.offset_locatie = "binnen beheergebied"

        bres_offset = offsets[idx]

        # 3. bres_offset vertalen naar polygoon
        mid_distance = bres_offset.project(self.punt)
        min_distance = max(mid_distance - self.lengte / 2, 0)
        max_distance = min(mid_distance + self.lengte / 2, bres_offset.length)
        line_start = bres_offset.interpolate(min_distance)
        line_end = bres_offset.interpolate(max_distance)
        distances = (bres_offset.project(Point(i)) for i in bres_offset.coords)
        line_vertices = [bres_offset.interpolate(i) for i in distances if (i > min_distance) and (i < max_distance)]
        bres_line = LineString(([line_start] + line_vertices + [line_end]))
        self.polygoon = bres_line.buffer(self.breedte / 2, cap_style="flat")

    def valide_oppervlak(self, afwijking: float = 0.02):
        if all((i is not None for i in (self.polygoon, self.lengte, self.breedte))):
            verhouding = self.polygoon.area / (self.lengte * self.breedte)
            return (1 - afwijking) < verhouding < (1 + afwijking)
        else:
            raise ValueError(
                "Je kunt alleen oppervlak controleren, wanneer je een polygoon, x2 en x3 gedefinieerd hebt."
            )


@dataclass
class Bressen:
    basisgegevens: BasisGegevens
    bressen: list[Bres] = field(default_factory=list)
    crs: CRS = field(default_factory=CRS.from_epsg(28992))

    def bereken_polygonen(self, offset, lengte, breedte):
        for bres in self.bressen:
            bres.calculate_polygon(offset=offset, lengte=lengte, breedte=breedte, basisgegevens=self.basisgegevens)

    @classmethod
    def from_gdf(cls, bressen_gdf, basisgegevens):
        bressen = [Bres.from_row(row) for row in bressen_gdf.itertuples()]
        return cls(bressen=bressen, basisgegevens=basisgegevens, crs=bressen_gdf.crs)
