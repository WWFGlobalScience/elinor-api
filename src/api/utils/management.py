import zipfile
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.geometries import MultiPolygon, OGRGeomType
from django.contrib.gis.geos import LinearRing, Polygon as GEOSPolygon
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from pathlib import Path
from tempfile import TemporaryDirectory


MAXIMUM_FILESIZE = 10485760  # 10MB
ACCEPTED_FILETYPES = ("application/zip", "application/x-zip-compressed")
ACCEPTED_EXTENSIONS = (".shp",)
ACCEPTED_GEOGCS = ("GEOGCS",)
ACCEPTED_EPSG = ("4326",)
POLYGON = "Polygon"
POLYGON25D = "Polygon25D"
MULTIPOLYGON = "MultiPolygon"
MULTIPOLYGON25D = "MultiPolygon25D"
ACCEPTED_GEOMETRIES = (POLYGON, POLYGON25D, MULTIPOLYGON, MULTIPOLYGON25D)


def get_extension_from_files(files):
    for file in files:
        ext = file.suffix
        if ext in ACCEPTED_EXTENSIONS:
            return ext

    return None


def get_zip_content(import_file_field, temppath):
    field = import_file_field.field.name
    import_file = import_file_field.file

    try:
        zf = zipfile.ZipFile(import_file)
        zf.extractall(temppath)
        dirs = [f for f in temppath.iterdir() if temppath.joinpath(f).is_dir()]
        files = [f for f in temppath.iterdir() if temppath.joinpath(f).is_file()]
        extension = get_extension_from_files(files)
        if extension is None and dirs:
            for d in dirs:
                subdir = temppath.joinpath(d)
                files = [f for f in subdir.iterdir() if subdir.joinpath(f).is_file()]
                extension = get_extension_from_files(files)
                if extension:
                    for file in files:
                        file.rename(temppath.joinpath(file.name))
                    break

        return extension

    except zipfile.BadZipfile:
        raise ValidationError({field: _("File is not a zip file")})


def clean_multipolygon(polygon):
    multi = None
    # print("input geom (OGR)")
    # print(polygon)
    # print(polygon.geom_type)
    # print(polygon.geom_count)
    # print(polygon.srid)
    if polygon.geom_type in ACCEPTED_GEOMETRIES:
        # print(polygon.geos.valid_reason)
        polygon.coord_dim = 2  # coerce 3D geometries to 2D
        polygon.close_rings()
        multi = polygon
        # Convert polygon of rings to multipolygon of polygons, to ensure dissolve
        if polygon.geom_type == POLYGON:
            multi = MultiPolygon(OGRGeomType(MULTIPOLYGON), srs=polygon.srid)
            for part in polygon:
                points = [(x, y) for x, y in zip(part.x, part.y)]
                ring = LinearRing(points)
                poly = GEOSPolygon(ring)
                multi.add(poly.ogr)

        if multi.empty:
            multi = None

    return multi


def get_multipolygon_from_geometries(geometries):
    """
    :param geometries: list of geometries of type Polygon or Multipolygon from django.contrib.gis.gdal.geometries
    :return: django.contrib.gis.gdal.geometries.Multipolygon or None
    """

    multipolygon = MultiPolygon(OGRGeomType(MULTIPOLYGON), srs=geometries[0].srid)
    for geometry in geometries:
        multi = clean_multipolygon(geometry)
        if multi:
            multipolygon.add(multi)
    # print("converted input geoms")
    # print(multipolygon)
    # print(multipolygon.geom_type)
    # print(multipolygon.srid)

    if multipolygon.empty:
        return None

    polygon = multipolygon.geos.unary_union.ogr
    returnmultipolygon = MultiPolygon(OGRGeomType(MULTIPOLYGON), srs=multipolygon.srid)
    returnmultipolygon.add(polygon)
    # print("output geom (OGR)")
    # print(returnmultipolygon)
    # print(returnmultipolygon.geom_type)
    # print(returnmultipolygon.srid)

    return returnmultipolygon


def get_multipolygon_from_shp(field, shapefiledir):
    try:
        ds = DataSource(shapefiledir)
        shp = ds[0]
    except (IndexError, GDALException) as e:
        raise ValidationError(
            {
                field: f"Error parsing shapefile. Are all sidecar files included? Exception: {e}"
            }
        )

    if (
        shp.srs["GEOGCS"] not in ACCEPTED_GEOGCS
        and shp.srs["AUTHORITY", 1] not in ACCEPTED_EPSG
    ):
        # TODO: Handle other CRSs by transforming
        crs_label = ""
        if shp.srs["PROJCS"] is not None:
            crs_label = shp.srs["PROJCS"]
        elif shp.srs["GEOGCS"] is not None:
            crs_label = shp.srs["GEOGCS"]
        if shp.srs["AUTHORITY"] is not None:
            crs_label = (
                f"{crs_label} ({shp.srs['AUTHORITY']} {shp.srs['AUTHORITY', 1]})"
            )
        raise ValidationError({field: f"Unsupported shapefile CRS: {crs_label}"})

    if shp.geom_type not in ACCEPTED_GEOMETRIES:
        raise ValidationError(
            {field: f"Unsupported shapefile geometry type: {shp.geom_type}"}
        )

    try:
        geometries = shp.get_geoms()
        multipolygon = get_multipolygon_from_geometries(geometries)
        return multipolygon

    except GDALException:
        raise ValidationError(
            {
                field: f"{shp.name} contains geometries that are empty, null, or otherwise invalid"
            }
        )


def get_multipolygon_from_import_file(import_file_field):
    field = import_file_field.field.name
    import_file = import_file_field.file
    multipolygon = None

    try:
        content_type = import_file.content_type
        if content_type not in ACCEPTED_FILETYPES:
            raise ValidationError({field: _(f"Filetype not supported: {content_type}")})
        if import_file.size > MAXIMUM_FILESIZE:
            raise ValidationError(
                {
                    field: _(
                        f"Filesize {filesizeformat(import_file.size)} exceeds "
                        f"maximum of {filesizeformat(MAXIMUM_FILESIZE)}"
                    )
                }
            )

        if content_type == "application/zip":
            with TemporaryDirectory() as tempdir:
                temppath = Path(tempdir)
                extension = get_zip_content(import_file_field, temppath)
                if extension is None:
                    raise ValidationError(
                        {
                            field: _(
                                f"No file with accepted extension found. Supported extensions: {ACCEPTED_EXTENSIONS}"
                            )
                        }
                    )

                if extension == ".shp":
                    multipolygon = get_multipolygon_from_shp(field, temppath)
                # handle other compressed filetypes here

        return multipolygon

    except AttributeError:
        raise ValidationError({field: _("File is missing an attribute")})
