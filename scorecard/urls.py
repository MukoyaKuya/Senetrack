from django.urls import path
from . import views

urlpatterns = [
    # PWA
    path("sw.js", views.service_worker, name="service-worker"),
    # Main Dashboard & Discovery
    path('', views.home, name='home'),
    path('senators/', views.senator_list, name='senator-list'),
    path('compare/', views.compare_senators, name='compare-senators'),
    path('insights/', views.data_insights, name='data-insights'),
    path('frontier/', views.frontier_insights, name='frontier-insights'),
    path('frontier/map/', views.frontier_map, name='frontier-map'),
    path('frontier/map/data/', views.frontier_map_data, name='frontier-map-data'),
    path('about/', views.about, name='about'),
    path('counties/', views.county_list, name='county-list'),
    path('county/<slug:slug>/', views.county_detail, name='county-detail'),
    path('senator/<str:senator_id>/', views.senator_detail, name='senator-detail'),
    
    # HTMX Partial Endpoints (The "Engines")
    path('senator/<str:senator_id>/engine/<str:engine_type>/', views.get_engine_partial, name='engine-partial'),
]
