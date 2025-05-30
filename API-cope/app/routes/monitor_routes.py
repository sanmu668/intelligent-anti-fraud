from flask import jsonify
import numpy as np
import pandas as pd
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
            stats = {
                'transaction_count': int(np.random.normal(1000, 100)),
                'risk_transaction_count': int(np.random.normal(50, 10)),
                'total_amount': float(np.random.normal(1000000, 100000)),
                'active_accounts': int(np.random.normal(500, 50)),
                'transaction_trend': float(np.random.normal(5, 2)),
                'risk_transaction_trend': float(np.random.normal(-2, 1)),
                'amount_trend': float(np.random.normal(3, 1)),
                'active_accounts_trend': float(np.random.normal(2, 0.5))
            }

            emit_realtime_update({
                'type': 'statistics',
                'data': stats
            })

            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/transactions', methods=['GET'])
    def get_monitor_transactions():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                data_cache.load_data()

            df = pd.DataFrame(data_cache.transactions)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            recent_transactions = df.sort_values('timestamp', ascending=False).head(100)

            transactions = []
            for _, row in recent_transactions.iterrows():
                transaction = {
                    'timestamp': row['timestamp'].isoformat(),
                    'transaction_type': row['type'],
                    'amount': float(row['amount']),
                    'source_account': row['nameOrig'],
                    'target_account': row['nameDest'],
                    'risk_score': float(row['risk_score'])
                }
                transactions.append(transaction)
            return jsonify(transactions)
        except Exception as e:
            logger.error(f"Error getting monitor transactions: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/alerts', methods=['GET'])
    def get_monitor_alerts():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                data_cache.load_data()
            alerts = []
            df = pd.DataFrame(data_cache.transactions)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            high_risk_txs = df[df['risk_score'] > 0.7].sort_values('timestamp', ascending=False).head(20)

            alert_templates = {
                '身份盗用': [
                    "检测到身份盗用风险",
                    "身份验证异常",
                    "账户身份信息不一致"
                ],
                '大额交易': [
                    "发现大额可疑转账",
                    "大额交易风险提示",
                    "异常大额交易预警"
                ],
                '洗钱行为': [
                    "检测到洗钱行为风险",
                    "多层资金转移预警",
                    "复杂资金清洗路径"
                ]
            }

            for idx, row in high_risk_txs.iterrows():
                if row['amount'] > 500000:
                    alert_type = '大额交易'
                elif row['risk_score'] > 0.85:
                    alert_type = '身份盗用'
                else:
                    alert_type = '洗钱行为'
                titles = alert_templates[alert_type]
                title_idx = hash(row['nameOrig'] + str(row['amount'])) % len(titles)
                title = titles[title_idx]
                description = f"账户 {row['nameOrig']} 向 {row['nameDest']} 发起 {row['type']} 交易，"
                description += f"金额 ¥{row['amount']:,.2f}，风险评分 {row['risk_score'] * 100:.0f}"
                severity = 'danger' if row['risk_score'] > 0.8 else 'warning'
                alert = {
                    'id': idx,
                    'timestamp': row['timestamp'].isoformat(),
                    'title': title,
                    'type': alert_type,
                    'description': description,
                    'severity': severity,
                    'risk_score': float(row['risk_score']),
                    'processed': False,
                    'details': {
                        'transaction_type': row['type'],
                        'amount': float(row['amount']),
                        'source_account': row['nameOrig'],
                        'target_account': row['nameDest']
                    }
                }
                alerts.append(alert)
            return jsonify(alerts)
        except Exception as e:
            logger.error(f"Error getting monitor alerts: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/latest-alerts', methods=['GET'])
    def get_latest_alerts():
        try:
            if not data_cache.alerts or not data_cache.last_update:
                data_cache.load_data()
            latest_alerts = []
            for alert in sorted(data_cache.alerts, key=lambda x: x['timestamp'], reverse=True)[:10]:
                alert_info = {
                    'timestamp': alert['timestamp'],
                    'type': alert['type'],
                    'risk_level': alert['risk_level'],
                    'description': alert['description'],
                    'status': alert['status']
                }
                latest_alerts.append(alert_info)
            return jsonify(latest_alerts)
        except Exception as e:
            logger.error(f"Error getting latest alerts: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/monitor/realtime-transactions', methods=['GET'])
    def get_realtime_transactions():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                data_cache.load_data()

            df = pd.DataFrame(data_cache.transactions)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            recent_transactions = df.sort_values('timestamp', ascending=False).head(100)
            transactions = []
            for _, row in recent_transactions.iterrows():
                transaction = {
                    'timestamp': row['timestamp'].isoformat(),
                    'amount': float(row['amount']),
                    'risk_score': float(row['risk_score']),
                    'risk_type': row['risk_type'],
                    'type': row['type']
                }
                transactions.append(transaction)
            return jsonify(transactions)
        except Exception as e:
            logger.error(f"Error getting realtime transactions: {e}")
            return jsonify({'error': str(e)}), 500 