from django.urls import path
from . import views

urlpatterns = [
    # Main Dashboard & Discovery
    path('', views.senator_list, name='index'),
    path('senator/<str:senator_id>/', views.senator_detail, name='senator-detail'),
    
    # HTMX Partial Endpoints (The "Engines")
    path('senator/<str:senator_id>/engine/<str:engine_type>/', views.get_engine_partial, name='engine-partial'),
]
