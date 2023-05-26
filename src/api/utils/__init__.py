import re
import subprocess
from typing import Optional


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
