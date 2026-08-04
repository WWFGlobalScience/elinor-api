import re
import subprocess
import traceback
from django.db.models.fields.related import ManyToManyField
from django.utils.html import strip_tags
from typing import Optional
from zipfile import ZipFile


def run_subprocess(command, std_input=None, to_file=None):
    kwargs = dict(check=True, capture_output=True, encoding="UTF-8", errors="replace")
    # subprocess.run only redirects stdin when `input` is given, so a child would
    # otherwise inherit our real stdin instead of seeing immediate EOF.
    if std_input is not None:
        kwargs["input"] = std_input
    else:
        kwargs["stdin"] = subprocess.DEVNULL

    try:
        proc = subprocess.run(command, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        if to_file is not None:
            try:
                with open(to_file, "w", encoding="UTF-8") as f:
                    f.write("DATA: \n")
                    f.write(str(e.stdout))
                    f.write("ERR: \n")
                    f.write(str(e.stderr))
            except OSError:
                traceback.print_exc()
        raise
    except Exception:
        print(command)
        raise

    # print things like NOTICEs and WARNINGs
    if proc.stderr:
        print(proc.stderr)

    if to_file is not None:
        with open(to_file, "w", encoding="UTF-8") as f:
            f.write("DATA: \n")
            f.write(str(proc.stdout))
            f.write("ERR: \n")
            f.write(str(proc.stderr))

    return proc.stdout, proc.stderr


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
