from dataclasses import dataclass, field
from typing import Optional, Union

import geopandas as gpd
import pandas as pd
from pyproj.crs.crs import CRS
from shapely.geometry import LineString, Point, Polygon

from bressen.basisgegevens import BasisGegevens
from bressen.exceptions import EmptyOffset, KeringNotFoundError
from bressen.geometries import get_closest_feature, get_containing_feature, get_offsets, project_point
from bressen.kering import get_kering_geometry
from bressen.styles import add_styles_to_geopackage


@dataclass
class Bres:
    fid: int
    punt: Point
    vlak: Optional[Polygon] = None
    offset: Optional[float] = None
    offset_locatie: Optional[str] = None
    breedte: Optional[float] = None
    lengte: Optional[float] = None
    fout: Optional[str] = None
    eigenschappen: Optional[dict] = dict

    @classmethod
    def from_row(cls, row):
        fid = row.Index
        punt = row.geometry
        eigenschappen = row._asdict()
        eigenschappen.pop("Index")
        eigenschappen.pop("geometry")
        return cls(fid=fid, punt=punt, eigenschappen=eigenschappen)


    def to_dict(self, geom_type: Union["punt", "vlak"], eigenschappen: bool=True):
        # fid
        data = {"fid": self.fid}
        
        # eigenschappen
        if eigenschappen:
            data = data | self.eigenschappen

        # class properties
        data = data | {f"bres_{i}":getattr(self,i) for i in ["offset", "offset_locatie", "breedte", "lengte", "fout"]}
        
        # geometry
        data["geometry"] = getattr(self,geom_type)

        return data
        


    def bereken_vlak(
        self, offset: float, lengte: float, breedte: float, basisgegevens: BasisGegevens, tolerantie=0.01
    ):
        self.offset = offset
        self.lengte = lengte
        self.breedte = breedte

        # 0. controlleer of punt wel een punt is
        if not isinstance(self.punt, Point):
            self.fout = f"Bres-locatie (punt) is geen shapely.geometry.Point (point-feature), maar: {self.punt}"
            return

        # 1. selecteer dichtsbijzijnde kering binnen tolerantie
        try:
            kering_geometry = get_kering_geometry(
                self.punt,
                keringen=basisgegevens.keringen,
                min_length=self.lengte,
                max_distance=tolerantie,
                max_line_extends=1,
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
                peilvlakken = [
                    get_containing_feature(geometry, basisgegevens.peilvlakken) for geometry in offset_points
                ]
                peilen = [i.peil if i is not None else None for i in peilvlakken]
                if all(peilen):  # (2) tussen twee peilvlakken, we kiezen laagste peil
                    if peilen[0] == peilen[1]:
                        self.fout = f"Peilvlak(ken) aan beiden zijden van bres hebben zelfde peil: {peilen[0]} m NAP op afstand {self.offset} m"
                        return
                    else:
                        idx = peilen.index(min(peilen))
                        self.offset_locatie = "laagste peilvlak"
                elif not any(peilen):
                    self.fout = f"Geen peilvlakken aan een zijde van bres binnen afstand {self.offset} m"
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
            line_vertices = [
                bres_offset.interpolate(i) for i in distances if (i > min_distance) and (i < max_distance)
            ]
            bres_line = LineString(([line_start] + line_vertices + [line_end]))
            self.vlak = bres_line.buffer(self.breedte / 2, cap_style="flat")

        except KeringNotFoundError:
            self.fout = f"Geen kering gevonden binnen gespecificeerde tolerantie {tolerantie} m"
        except EmptyOffset:
            self.fout = f"Geen valide offset aan beide zijden van bres met gegeven tolerantie {tolerantie} m"

    def afwijking_oppervlak(self, afwijking: float = 0.02, raise_error=True):
        """Controleer of polygon.area een grote afwijking heeft ten opzichte van lengte x breedte."""
        if all((i is not None for i in (self.vlak, self.lengte, self.breedte))):
            verhouding = self.vlak.area / (self.lengte * self.breedte)
            return not ((1 - afwijking) < verhouding < (1 + afwijking))
        else:
            if raise_error:
                raise ValueError(
                    "Je kunt alleen oppervlak controleren, wanneer je een polygoon, lengte en breedte van de bres gedefinieerd hebt."
                )
            else:
                return None

    def snijdt_kering(self, keringen, raise_error=True):
        """Controleer of polgon kering snijdt."""
        if self.vlak is not None:
            kering = get_closest_feature(self.vlak, keringen)
            if kering is not None:
                return self.vlak.intersects(kering.geometry)
            else:
                return False
        else:
            if raise_error:
                raise ValueError(
                    "Je kunt alleen controleren of polygoon een kering snijdt, wanneer de polygoon is gedefinieerd."
                )
            else:
                return None

    def snijdt_watervlak(self, watervlakken, raise_error=True):
        """Controleer of polgon watervlak snijdt."""
        if self.vlak is not None:
            watervlak = get_closest_feature(self.vlak, watervlakken)
            if watervlak is not None:
                return self.vlak.intersects(watervlak.geometry)
            else:
                return False
        else:
            if raise_error:
                raise ValueError(
                    "Je kunt alleen controleren of polygoon een watervlak snijdt, wanneer de polygoon is gedefinieerd."
                )
            else:
                return None


@dataclass
class Bressen:
    basisgegevens: BasisGegevens
    bressen: list[Bres] = field(default_factory=list)
    crs: CRS = field(default_factory=CRS.from_epsg(28992))

    def bereken_vlakken(self, offset, lengte, breedte):
        for bres in self.bressen:
            bres.bereken_vlak(offset=offset, lengte=lengte, breedte=breedte, basisgegevens=self.basisgegevens)

    @classmethod
    def from_gdf(cls, bressen_gdf, basisgegevens):
        bressen = [Bres.from_row(row) for row in bressen_gdf.itertuples()]
        return cls(bressen=bressen, basisgegevens=basisgegevens, crs=bressen_gdf.crs)

    def check_fids(self):
        fids = [i.fid for i in self.bressen]
        duplicated_fids = [i for i in fids if fids.count(i)  > 1]
        if duplicated_fids:
            raise ValueError(f"Bres.bressen mag alleen unique fids bevatten. De volgende fids komen meermaals voor: {duplicated_fids}")

    
    def get_bres(self, fid:int):
        self.check_fids()
        return next((i for i in self.bressen if i.fid == fid), None)

    def to_gdf(
        self,
        eigenschappen: bool = True,
        geom_type: Union["punt", "vlak"] = "vlak",
        validatie: bool = True,
        afwijking: float = 0.02,
    ):
        # get gdf
        data = [i.to_dict(eigenschappen=eigenschappen, geom_type=geom_type) for i in self.bressen]
        gdf = gpd.GeoDataFrame(data, crs=self.crs)
        gdf.set_index("fid", inplace=True)

        # add validations
        if validatie:
            gdf.loc[:, "afwijking_oppervlak"] = [
                i.afwijking_oppervlak(afwijking, raise_error=False) for i in self.bressen
            ]

            gdf.loc[:, "snijdt_kering"] = [
                i.snijdt_kering(self.basisgegevens.keringen, raise_error=False) for i in self.bressen
            ]

            gdf.loc[:, "snijdt_watervlak"] = [
                i.snijdt_watervlak(self.basisgegevens.watervlakken, raise_error=False) for i in self.bressen
            ]

        return gdf

    def to_gpkg(self, file_path, eigenschappen: bool = True, validatie: bool = True, afwijking: float = 0.02):
        # bressen      
        gdf = self.to_gdf(eigenschappen=eigenschappen, geom_type="punt", validatie=validatie, afwijking=afwijking)
        gdf.to_file(file_path, layer="bressen", engine="pyogrio")

        # vlakken
        gdf = self.to_gdf(eigenschappen=eigenschappen, geom_type="vlak", validatie=validatie, afwijking=afwijking)
        gdf[gdf.geometry.isna()].to_file(file_path, layer="fouten", engine="pyogrio")
        gdf[gdf.geometry.notna()].to_file(file_path, layer="bresvlakken", engine="pyogrio")

        # style-tabel toevoegen
        add_styles_to_geopackage(file_path)
