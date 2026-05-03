from django.urls import path
from .views import optimize_route

urlpatterns = [
    path('optimize/', optimize_route),
]