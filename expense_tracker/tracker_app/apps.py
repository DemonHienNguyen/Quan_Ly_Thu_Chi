from django.apps import AppConfig


class TrackerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker_app'
    verbose_name = 'Quản lý Thu Chi'

    def ready(self):
        # Đảm bảo tính tương thích giữa Django và môi trường Python 3.15 mới nhất
        from django.template import context as django_context

        def _base_context_copy(self):
            duplicate = self.__class__.__new__(self.__class__)
            duplicate.dicts = self.dicts[:]
            return duplicate

        django_context.BaseContext.__copy__ = _base_context_copy
        
        # Import templatetags to register custom filters
        import tracker_app.templatetags.currency_filters  # noqa
