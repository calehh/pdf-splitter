import flask_migrate


def init_app(app, db):
    flask_migrate.Migrate(app, db,compare_type=True)
