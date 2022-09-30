import csv
from . import BaseReport


class Echo(object):
    """An object that implements just the write method of the file-like interface."""

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class CSVReport(BaseReport):
    def _flatten_record(self, record_dict):
        for k, v in record_dict.items():
            if isinstance(v, (list, set, tuple)):
                record_dict[k] = ",".join([str(e) for e in v])
            else:
                record_dict[k] = v

        return record_dict

    def _apply_formatters(self, flat_record):
        return self._flatten_record(flat_record)

    def stream(self, fields, data, *args, **kwargs):
        if data is None:
            yield ""
        csv_buffer = Echo()
        csv_writer = csv.DictWriter(
            csv_buffer,
            fieldnames=fields,
            extrasaction="ignore",
            quoting=csv.QUOTE_NONNUMERIC,
        )

        yield csv_buffer.write(f"{','.join(fields)}\n")
        for flat_record in data:
            yield csv_writer.writerow(self._apply_formatters(flat_record))

    def generate(self, path, fields, data, *args, **kwargs):
        with open(path, "wb") as csvfile:
            csv_writer = csv.DictWriter(
                csvfile,
                fieldnames=fields,
                extrasaction="ignore",
                quoting=csv.QUOTE_NONNUMERIC,
            )
            csv_writer.writeheader()
            for flat_record in data:
                csv_writer.writerow(self._apply_formatters(flat_record))
