class AnalyzerRouter:
    """
    A router to control database operations for the analyzer_db.
    """

    def db_for_read(self, model, **hints):
        """Directs read operations for analyzer app to analyzer_db."""
        if model._meta.app_label == 'analyzer':  # FIXED HERE
            return 'analyzer_db'
        return None

    def db_for_write(self, model, **hints):
        """Directs write operations for analyzer app to analyzer_db."""
        if model._meta.app_label == 'analyzer':  # FIXED HERE
            return 'analyzer_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations only within the same database."""
        if obj1._meta.app_label == 'analyzer' and obj2._meta.app_label == 'analyzer':
            return True
        if obj1._meta.app_label != 'analyzer' and obj2._meta.app_label != 'analyzer':
            return True
        return False  # Prevent cross-database relations

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure only 'analyzer' migrations go to 'analyzer_db'.
        """
        if db == 'analyzer_db':
            return app_label == 'analyzer'  # FIXED HERE
        return None  # Let Django handle other databases
