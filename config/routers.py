class PollutionRouter:
    route_app_labels = {"measurements"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:  # noqa: SLF001
            return "timeseries"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:  # noqa: SLF001
            return "timeseries"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.route_app_labels  # noqa: SLF001
            or obj2._meta.app_label in self.route_app_labels  # noqa: SLF001
        ):
            if obj1._meta.app_label == 'users' or obj2._meta.app_label == 'users':
                return True
            return obj1._meta.app_label == obj2._meta.app_label  # noqa: SLF001
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == "timeseries"

        if db == "timeseries":
            return False

        return "default"
