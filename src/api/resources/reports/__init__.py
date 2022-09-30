from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework_gis.pagination import GeoJsonPagination
from ..base import BaseAPIViewSet


def datetime2date(obj, fieldname):
    datetime = getattr(obj, fieldname)
    if not datetime:
        return None
    return datetime.date().isoformat()


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


class ReportView(BaseAPIViewSet):
    http_method_names = [method.lower() for method in SAFE_METHODS]
    # drf_label = ""
    serializer_class_geojson = None
    serializer_class_csv = None

    @action(detail=False, methods=["get"])
    def json(self, request, *args, **kwargs):  # default, for completeness
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def geojson(self, request, *args, **kwargs):
        self.serializer_class = self.serializer_class_geojson
        self.pagination_class = BaseGeoJsonPagination
        return self.list(request, *args, **kwargs)

    # TODO: implement csv view
    # @action(detail=False, methods=["get"])
    # def csv(self, request, *args, **kwargs):
    #
    #     queryset = self.filter_queryset(self.get_queryset())
    #     return csv_report.get_csv_response(
    #         queryset,
    #         self.serializer_class_csv,
    #         # see about getting file_name_prefix from serializer_class_csv, inheriting from or same as serializer_class
    #         file_name_prefix=file_name_prefix,
    #     )
