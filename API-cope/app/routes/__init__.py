from flask import Flask
from flask_socketio import SocketIO
from .dashboard_routes import register_dashboard_routes
from .monitor_routes import register_monitor_routes
from .analysis_routes import register_analysis_routes
from .group_routes import register_group_routes
from .alert_routes import register_alert_routes
from .graph_routes import register_graph_routes

def register_routes(app: Flask, socketio: SocketIO, data_cache):
    """Register all application routes"""
    register_dashboard_routes(app, data_cache)
    register_monitor_routes(app, socketio, data_cache)
    register_analysis_routes(app, data_cache)
    register_group_routes(app, data_cache)
    register_alert_routes(app, data_cache)
    register_graph_routes(app, data_cache) 