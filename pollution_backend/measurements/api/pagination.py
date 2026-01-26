from rest_framework.pagination import PageNumberPagination, CursorPagination

class MeasurementCursorPagination(CursorPagination):
    page_size = 100
    ordering = '-time'
    cursor_query_param = 'cursor'

class MeasurementPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 10000