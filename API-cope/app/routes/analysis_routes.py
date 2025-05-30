from flask import jsonify, request
import pandas as pd
from app.utils.logger import logger

def register_analysis_routes(app, data_cache):
    @app.route('/api/analysis/trends', methods=['GET'])
    def get_analysis_trends():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                data_cache.load_data()
            trend_type = request.args.get('type', 'week')
            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')
            df = pd.DataFrame(data_cache.transactions)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if start_date and end_date:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
            if trend_type == 'week':
                df['time_group'] = df['timestamp'].dt.strftime('%Y-%m-%d')
                time_format = '%m-%d'
            else:  # month
                df['time_group'] = df['timestamp'].dt.strftime('%Y-%m')
                time_format = '%Y-%m'
            daily_stats = df.groupby('time_group').agg({
                'amount': 'count',
                'risk_score': lambda x: (
                    sum(x > 0.8),
                    sum((x > 0.6) & (x <= 0.8)),
                    len(x)
                )
            }).reset_index()

            dates = daily_stats['time_group'].tolist()
            high_risk = [x[0] for x in daily_stats['risk_score']]
            suspicious = [x[1] for x in daily_stats['risk_score']]
            total = daily_stats['amount'].tolist()
            return jsonify({
                'xAxis': dates,
                'series': [
                    {
                        'name': '高风险交易',
                        'type': 'line',
                        'data': high_risk,
                        'itemStyle': {'color': '#F56C6C'}
                    },
                    {
                        'name': '可疑交易',
                        'type': 'line',
                        'data': suspicious,
                        'itemStyle': {'color': '#E6A23C'}
                    },
                    {
                        'name': '总交易量',
                        'type': 'line',
                        'data': total,
                        'itemStyle': {'color': '#409EFF'}
                    }
                ]
            })
        except Exception as e:
            logger.error(f"Error getting analysis trends: {e}")
            return jsonify({'error': str(e)}), 500 