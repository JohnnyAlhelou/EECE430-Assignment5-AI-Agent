from django.contrib import admin
from django.urls import path

from chat.views import chat_view, reset_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", chat_view, name="chat"),
    path("reset/", reset_view, name="reset"),
]