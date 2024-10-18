import re
import subprocess
from django.db.models.fields.related import ManyToManyField
from django.utils.html import strip_tags
from typing import Optional
from zipfile import ZipFile


def run_subprocess(command, std_input=None, to_file=None):
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except Exception as e:
        print(command)
        raise e

    data, err = proc.communicate(input=std_input)

    if to_file is not None:
        with open(to_file, "w") as f:
            f.write("DATA: \n")
            f.write(str(data))
            f.write("ERR: \n")
            f.write(str(err))
    else:
        return data, err


def slugify(text: str, separator: Optional[str] = "_") -> str:
    text = re.sub(r"[^\w\s" + re.escape(separator) + "]", "", text.lower())
    text = re.sub(r"[\s_]+", separator, text)
    text = text.strip(" " + separator)

    return text


def truthy(val):
    return val in ("t", "T", "true", "True", "TRUE", True, 1)


def strip_html(val):
    val = val or ""
    val = strip_tags(val)

    return val.strip()


def unzip_file(file, temppath):
    zf = ZipFile(file)
    zf.extractall(temppath)
    dirs = [f for f in temppath.iterdir() if temppath.joinpath(f).is_dir()]
    files = [f for f in temppath.iterdir() if temppath.joinpath(f).is_file()]
    return dirs, files


def get_m2m_fields(model):
    return [field.name for field in model._meta.get_fields() if isinstance(field, ManyToManyField)]
