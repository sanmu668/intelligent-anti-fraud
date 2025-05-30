from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from app.utils.logger import setup_logger
from app.routes import register_routes
from app.utils.data_cache import DataCache

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)
    
    # Initialize logger
    setup_logger()
    
    # Initialize data cache
    data_cache = DataCache()
    
    # Register routes
    register_routes(app, socketio, data_cache)
    
    return app, socketio

if __name__ == '__main__':
    print("Starting server with WebSocket support...")
    app, socketio = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) 