from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    path('', views.orbits, name='home'),  # página principal
    path('orbits/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('api/planet-info/', views.planet_info_api, name='planet_info_api'),
    path('api/space-weather/', views.space_weather_api, name='space_weather_api'),
    path('api/orbit-positions/', views.orbit_positions_api, name='orbit_positions_api'),
]
