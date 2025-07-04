from django.apps import AppConfig


class NewApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'new_application'

    def ready(self):
        # Import and start the Redis listener for frame streaming
        from . import views
        views.start_redis_listener()
