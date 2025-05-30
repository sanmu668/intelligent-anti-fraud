from flask import jsonify
from app.services.monitor_service import (
    get_monitor_stats,
    get_monitor_transactions_data,
    get_monitor_alerts_data,
    get_latest_alerts_data,
    get_realtime_transactions_data
)
from app.utils.logger import logger

def register_monitor_routes(app, socketio, data_cache):
    @socketio.on('connect', namespace='/ws/monitor')
    def handle_connect():
        print('Client connected to monitor websocket')
        socketio.emit('connection_status', {'status': 'connected'}, namespace='/ws/monitor')

    @socketio.on('disconnect', namespace='/ws/monitor')
    def handle_disconnect():
        print('Client disconnected from monitor websocket')

    @socketio.on_error(namespace='/ws/monitor')
    def handle_error(e):
        print('WebSocket error:', str(e))

    def emit_realtime_update(data):
        try:
            socketio.emit('update', data, namespace='/ws/monitor')
        except Exception as e:
            print('Error emitting update:', str(e))

    @app.route('/api/monitor/statistics', methods=['GET'])
    def get_monitor_statistics():
        try:
            stats = get_monitor_stats()
            if 'error' in stats:
                return jsonify({'error': stats['error']}), 500

            emit_realtime_update({
                'type': 'statistics',
                'data': stats
            })

            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error in monitor statistics route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/transactions', methods=['GET'])
    def get_monitor_transactions():
        try:
            transactions = get_monitor_transactions_data(data_cache)
            if 'error' in transactions:
                return jsonify({'error': transactions['error']}), 500
            return jsonify(transactions)
        except Exception as e:
            logger.error(f"Error in monitor transactions route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/alerts', methods=['GET'])
    def get_monitor_alerts():
        try:
            alerts = get_monitor_alerts_data(data_cache)
            if 'error' in alerts:
                return jsonify({'error': alerts['error']}), 500
            return jsonify(alerts)
        except Exception as e:
            logger.error(f"Error in monitor alerts route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/latest-alerts', methods=['GET'])
    def get_latest_alerts():
        try:
            alerts = get_latest_alerts_data(data_cache)
            if 'error' in alerts:
                return jsonify({'error': alerts['error']}), 500
            return jsonify(alerts)
        except Exception as e:
            logger.error(f"Error in latest alerts route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/realtime-transactions', methods=['GET'])
    def get_realtime_transactions():
        try:
            transactions = get_realtime_transactions_data(data_cache)
            if 'error' in transactions:
                return jsonify({'error': transactions['error']}), 500
            return jsonify(transactions)
        except Exception as e:
            logger.error(f"Error in realtime transactions route: {e}")
            return jsonify({'error': str(e)}), 500 