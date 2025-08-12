from dataset_profiler.routes import profiler
from dataset_profiler.routes import health


def initialize_routes(app):
    app.include_router(profiler.router)
    app.include_router(health.router)
