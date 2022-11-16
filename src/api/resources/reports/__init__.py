from collections import OrderedDict
from datetime import datetime
from django.http import StreamingHttpResponse
from django.utils import translation
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework_gis.pagination import GeoJsonPagination
from ..base import BaseAPIViewSet
from ...reports import CSVReport


def datetime2date(obj, fieldname):
    datetime = getattr(obj, fieldname)
    if not datetime:
        return None
    return datetime.date().isoformat()


def get_flattened(base, fielddict):
    flattened_fields = []
    for k, v in fielddict.items():
        subfield_name = f"{base}__{k}"
        flattened_fields.append({subfield_name: v})

    return flattened_fields


class BaseGeoJsonPagination(GeoJsonPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 5000


class BaseReportSerializer(serializers.ModelSerializer):
    created_on = serializers.SerializerMethodField()
    created_by = serializers.CharField(source="created_by.get_full_name")
    updated_on = serializers.SerializerMethodField()
    updated_by = serializers.CharField(source="updated_by.get_full_name")

    def get_created_on(self, obj):
        return datetime2date(obj, "created_on")

    def get_updated_on(self, obj):
        return datetime2date(obj, "updated_on")


class CSVReportMixin(BaseAPIViewSet):
    """
    Generates fields and data suitable for generating a csv using the base serializer
    defined for the view, respecting field order and naming.
    OneToOne relationships (nested serializer without many=True) are automatically flattened.
    Custom manipulation can be specified via get_<fieldname> callable similar to SerializerMethodField appraoch.
    """

    csv_method_fields = []
    file_prefix = ""

    def get_fields(self):
        serializer = self.get_serializer(many=True)
        fields = serializer.child.get_fields()

        flat_fields = []
        for fieldname, field in fields.items():
            if fieldname in self.csv_method_fields:
                methodname = f"get_{fieldname}"
                method = getattr(self, methodname)
                expand_fields = [key for d in method() for key in d]
                flat_fields.extend(expand_fields)
            elif isinstance(field, serializers.Serializer):
                related_fields = get_flattened(fieldname, field.get_fields())
                related_field_keys = [key for f in related_fields for key in f]
                flat_fields.extend(related_field_keys)
            else:
                flat_fields.append(fieldname)

        return flat_fields

    def get_data(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg in self.kwargs:
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            queryset = queryset.filter(**filter_kwargs)
        serializer = self.get_serializer(queryset, many=True)

        data = []
        for record in serializer.data:
            rowdata = {}
            for fieldname, value in record.items():
                if fieldname in self.csv_method_fields:
                    methodname = f"get_{fieldname}"
                    method = getattr(self, methodname)
                    fields = method(value)
                elif isinstance(value, OrderedDict):
                    fields = get_flattened(fieldname, value)
                else:
                    fields = [{fieldname: value}]

                for field in fields:
                    rowdata.update(field)

            data.append(rowdata)

        return data

    def get_csv_response(self):
        fields = self.get_fields()
        data = self.get_data()
        time_stamp = datetime.utcnow().strftime("%Y%m%d")
        lang = translation.get_language()
        file_name = f"{self.file_prefix}-{time_stamp}-{lang}.csv".lower()

        report = CSVReport()
        # assumes all fields present in all items
        stream = report.stream(fields, data)

        response = StreamingHttpResponse(stream, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response


class ReportView(CSVReportMixin, BaseAPIViewSet):
    http_method_names = [method.lower() for method in SAFE_METHODS]
    serializer_class_geojson = None

    @action(detail=False, methods=["get"])
    def json(self, request, *args, **kwargs):  # default, for completeness
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def geojson(self, request, *args, **kwargs):
        self.serializer_class = self.serializer_class_geojson
        self.pagination_class = BaseGeoJsonPagination
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def csv(self, request, *args, **kwargs):
        return self.get_csv_response()

    @action(detail=True, methods=["get"])
    def csv_detail(self, request, *args, **kwargs):
        return self.get_csv_response()
