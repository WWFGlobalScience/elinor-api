import tempfile
import shutil
import zipfile
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from os import listdir
from os.path import isdir, isfile, join, splitext


MAXIMUM_FILESIZE = 10485760  # 10MB
ACCEPTED_FILETYPES = ("application/zip",)
ACCEPTED_EXTENSIONS = (".shp",)


def get_extension_from_files(files):
    for file in files:
        filename, ext = splitext(file)
        if ext in ACCEPTED_EXTENSIONS:
            return ext

    return None


def get_zip_content(import_file):
    field = import_file.field_name
    tempdir = tempfile.mkdtemp()
    contentdir = tempdir

    try:
        zf = zipfile.ZipFile(import_file.file)
        zf.extractall(tempdir)
        contents = listdir(tempdir)
        dirs = [f for f in contents if isdir(join(tempdir, f))]
        files = [f for f in contents if isfile(join(tempdir, f))]
        extension = get_extension_from_files(files)
        if extension is None and dirs:
            for d in dirs:
                subdir = join(tempdir, d)
                files = [f for f in listdir(subdir) if isfile(join(subdir, f))]
                extension = get_extension_from_files(files)
                if extension:
                    contentdir = subdir
                    break

        return contentdir, extension

    except zipfile.BadZipfile:
        raise ValidationError({field: _("File is not a zip file")})


def get_multipolygon_from_shp(shapefiledir):
    # check for required shp files
    # check CRS
    # check geometry is polygon/multipolygon
    # loop over features:
    # ensure valid geometry/multipolygon
    # see about combining all records' polygons
    #     shapely - https://shapely.readthedocs.io/en/stable/manual.html#shapely.ops.unary_union
    #     geos - https://docs.djangoproject.com/en/3.2/ref/contrib/gis/geos/#geos-tutorial
    #     return GEOSGeometry multipolygon
    return shapefiledir


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
            # TODO: figure out how to ensure tempdir always gets cleaned up
            contentdir, extension = get_zip_content(import_file)
            if extension is None:
                raise ValidationError(
                    {field: _(f"No file with accepted extension found. Supported extensions: {ACCEPTED_EXTENSIONS}")}
                )

            if extension == ".shp":
                polygon = get_multipolygon_from_shp(contentdir)
            # handle other compressed filetypes here

        # return polygon
        return import_file

    except AttributeError:
        raise ValidationError({field: _("File is missing an attribute")})
