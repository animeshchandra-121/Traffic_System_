from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/get_signal_states/', views.get_signal_states, name='get_signal_states'),
    path('video_feed/<int:signal_id>/', views.video_feed, name='video_feed'),
    path('api/emergency/', views.update_emergency_mode, name='update_emergency_mode'),
    path('api/upload_video/', views.upload_video, name = 'upload_video'),
    path('', views.dashboard_view, name='dashboard'),
    path('api/save_area/', views.save_area, name='save_area'),
    path('api/get_video_sources/', views.get_video, name='get_video'),
    path('api/get_area/', views.get_area, name="get_area"),
    path('api/add_junction/', views.add_junction, name = "add_junction"),
    path('api/analytics/', views.get_dashboard_analytics_data, name='dashboard_analytics_api'),
    path('api/start_workers_api/', views.start_workers_api, name='start_workers_api'),
    path('api/stop_workers_api/', views.stop_workers_api, name='stop_workers_api')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
