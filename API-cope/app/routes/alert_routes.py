from flask import jsonify, request
import pandas as pd
from datetime import datetime
from app.utils.logger import logger

def register_alert_routes(app, data_cache):
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                data_cache.load_data()
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('pageSize', 20, type=int)
            alert_type = request.args.get('alertType', '')
            risk_level = request.args.get('riskLevel', '')
            status = request.args.get('status', '')
            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')

            df = pd.DataFrame(data_cache.transactions)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            if start_date and end_date:
                try:
                    start = pd.to_datetime(start_date).tz_localize(None)
                    end = pd.to_datetime(end_date).tz_localize(None)
                    logger.info(f"Filtering data between {start} and {end}")

                    if df['timestamp'].dt.tz is not None:
                        df['timestamp'] = df['timestamp'].dt.tz_localize(None)

                    df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                    logger.info(f"Filtered data shape: {df.shape}")
                except Exception as e:
                    logger.error(f"Error parsing dates: {e}")
                    return jsonify({
                        'error': f'Invalid date format: {str(e)}'
                    }), 400

            alerts = []
            high_risk_txs = df[df['risk_score'] > 0.7]
            logger.info(f"Found {len(high_risk_txs)} high risk transactions")
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
            for _, row in high_risk_txs.iterrows():
                if row['amount'] > 500000:
                    alert_type_name = '大额交易'
                elif row['risk_score'] > 0.85:
                    alert_type_name = '身份盗用'
                else:
                    alert_type_name = '洗钱行为'
                titles = alert_templates[alert_type_name]
                title_idx = hash(row['nameOrig'] + str(row['amount'])) % len(titles)
                title = titles[title_idx]
                description = f"账户 {row['nameOrig']} 向 {row['nameDest']} 发起 {row['type']} 交易，"
                description += f"金额 ¥{row['amount']:,.2f}，风险评分 {row['risk_score'] * 100:.0f}"
                risk_level_name = '高风险' if row['risk_score'] > 0.8 else '中风险'
                alert = {
                    'id': len(alerts) + 1,
                    'time': row['timestamp'].isoformat(),
                    'type': alert_type_name,
                    'title': title,
                    'description': description,
                    'riskLevel': risk_level_name,
                    'status': '未处理',
                    'handler': '-',
                    'details': {
                        'transaction_type': row['type'],
                        'amount': float(row['amount']),
                        'risk_score': float(row['risk_score']),
                        'source_account': row['nameOrig'],
                        'target_account': row['nameDest']
                    }
                }
                alerts.append(alert)
            filtered_alerts = alerts
            if alert_type:
                filtered_alerts = [a for a in filtered_alerts if a['type'] == alert_type]
            if risk_level:
                filtered_alerts = [a for a in filtered_alerts if a['riskLevel'] == risk_level]
            if status:
                filtered_alerts = [a for a in filtered_alerts if a['status'] == status]
            filtered_alerts.sort(key=lambda x: x['time'], reverse=True)
            total = len(filtered_alerts)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paged_alerts = filtered_alerts[start_idx:end_idx]
            return jsonify({
                'total': total,
                'items': paged_alerts
            })

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alerts/batch-process', methods=['POST'])
    def batch_process_alerts():
        try:
            data = request.json
            alert_ids = data.get('alertIds', [])
            method = data.get('method')
            description = data.get('description')
            handler = data.get('handler', 'System')
            response = {
                'success': True,
                'message': f'Processed {len(alert_ids)} alerts',
                'data': {
                    'alert_ids': alert_ids,
                    'method': method,
                    'description': description,
                    'handler': handler,
                    'process_time': datetime.now().isoformat()
                }
            }
            return jsonify(response)
        except Exception as e:
            logger.error(f"Error batch processing alerts: {e}")
            return jsonify({'error': str(e)}), 500 