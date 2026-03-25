from django.urls import path
from . import views

app_name = "scorecard"

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
    path('insights/export/csv/', views.export_insights_csv, name='insights-export-csv'),
    path('about/', views.about, name='about'),
    path('bills/', views.bills_tracker, name='bills-tracker'),
    path('bills/analytics/', views.bills_analytics, name='bills-analytics'),
    path('counties/', views.county_list, name='county-list'),
    path('county/<slug:slug>/', views.county_detail, name='county-detail'),
    path('senator/<str:senator_id>/', views.senator_detail, name='senator-detail'),
    
    # HTMX Partial Endpoints (The "Engines")
    path('senator/<str:senator_id>/engine/<str:engine_type>/', views.get_engine_partial, name='engine-partial'),
]
