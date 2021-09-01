import zipfile
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.gdal.error import GDALException
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from pathlib import Path
from tempfile import TemporaryDirectory


MAXIMUM_FILESIZE = 10485760  # 10MB
ACCEPTED_FILETYPES = ("application/zip",)
ACCEPTED_EXTENSIONS = (".shp",)
ACCEPTED_GEOGCS = ("GEOGCS",)
ACCEPTED_EPSG = ("4326",)


def get_extension_from_files(files):
    for file in files:
        ext = file.suffix
        if ext in ACCEPTED_EXTENSIONS:
            return ext

    return None


def get_zip_content(import_file, temppath):
    field = import_file.field_name

    try:
        zf = zipfile.ZipFile(import_file.file)
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


def get_multipolygon_from_shp(import_file, shapefiledir):
    field = import_file.field_name
    polygon = None
    try:
        ds = DataSource(shapefiledir)
        shp = ds[0]
        # print(type(shp))
        # print(dir(shp))
        # print(shp.__dict__)
    except (IndexError, GDALException) as e:
        raise ValidationError({field: f"Error parsing shapefile. Are all sidecar files included? Exception: {e}"})

    if shp.srs["GEOGCS"] not in ACCEPTED_GEOGCS and shp.srs["AUTHORITY", 1] not in ACCEPTED_EPSG:
        # TODO: Handle other CRSs by transforming
        raise ValidationError({field: f"Unsupported shapefile CRS: {shp.srs}"})

    # TODO: check geometry is polygon/multipolygon, try both
    # TODO: After handling geometries below, see if it matters which one / coerce
    print(shp.geom_type)
    # TODO: loop over features: -- try multiple
    print(shp.get_geoms())
    # ensure valid geometry/multipolygon
    # see about combining all records' polygons
    #     shapely - https://shapely.readthedocs.io/en/stable/manual.html#shapely.ops.unary_union
    #     geos - https://docs.djangoproject.com/en/3.2/ref/contrib/gis/geos/#geos-tutorial
    #     return GEOSGeometry multipolygon

    return polygon


def get_multipolygon_from_import_file(import_file):
    field = import_file.field_name
    polygon = None

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
                extension = get_zip_content(import_file, temppath)
                if extension is None:
                    raise ValidationError(
                        {field: _(f"No file with accepted extension found. Supported extensions: {ACCEPTED_EXTENSIONS}")}
                    )

                if extension == ".shp":
                    polygon = get_multipolygon_from_shp(import_file, temppath)
                # handle other compressed filetypes here

        return polygon

    except AttributeError:
        raise ValidationError({field: _("File is missing an attribute")})
