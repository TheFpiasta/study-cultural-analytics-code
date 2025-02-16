class AnalyzerRouter:
    """
    A router to control database operations for the analyzer_db.
    """

    def db_for_read(self, model, **hints):
        """Direct read operations for analyzer app to analyzer_db."""
        if model._meta.app_label == "analyzer":
            return "analyzer_db"
        return None  # Let Django decide for other apps

    def db_for_write(self, model, **hints):
        """Direct write operations for analyzer app to analyzer_db."""
        if model._meta.app_label == "analyzer":
            return "analyzer_db"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations only within the same database."""
        if obj1._meta.app_label == "analyzer" and obj2._meta.app_label == "analyzer":
            return True
        if obj1._meta.app_label != "analyzer" and obj2._meta.app_label != "analyzer":
            return True
        return False  # Prevent cross-database relations

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure analyzer models go ONLY to analyzer_db and NOT default."""
        if app_label == "analyzer":
            return db == "analyzer_db"  # Block migrations in default
        return db == "default"  # Let Django handle other apps normally
