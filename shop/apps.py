# from django.apps import AppConfig


# class PublicViewConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'shop'


from django.apps import AppConfig


class PublicViewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"

    def ready(self):
        import shop.signals