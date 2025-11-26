from dataset_profiler.routes import profiler
from dataset_profiler.routes import health
from dataset_profiler.routes import auth


def initialize_routes(app):
    app.include_router(profiler.router)
    app.include_router(health.router)
    app.include_router(auth.router)
