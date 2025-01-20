from rest_framework.urlpatterns import format_suffix_patterns

from django.urls import re_path

from .views import LocationsEndpoint, NotificationsEndpoint, OrgsEndpoint, ShortcutsEndpoint, TemplatesEndpoint

urlpatterns = [
    # ========== endpoints A-Z ===========
    re_path(r"^locations$", LocationsEndpoint.as_view(), name="api.internal.locations"),
    re_path(r"^notifications$", NotificationsEndpoint.as_view(), name="api.internal.notifications"),
    re_path(r"^shortcuts$", ShortcutsEndpoint.as_view(), name="api.internal.shortcuts"),
    re_path(r"^templates$", TemplatesEndpoint.as_view(), name="api.internal.templates"),
    re_path(r"^orgs$", OrgsEndpoint.as_view(), name="api.internal.orgs"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=["json"])
