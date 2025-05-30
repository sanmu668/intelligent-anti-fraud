from flask import jsonify, request
import pandas as pd
import numpy as np
import networkx as nx
from app.services.group_service import (
    get_group_heatmap_data,
    get_group_behavior_radar_data,
    get_random_accounts_data
)
from app.utils.logger import logger

def register_group_routes(app, data_cache):
    @app.route('/api/group/heatmap', methods=['GET'])
    def get_group_heatmap():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                logger.info("Loading data cache...")
                data_cache.load_data()
            min_risk = request.args.get('min_risk', type=float, default=0.5)
            min_amount = request.args.get('min_amount', type=float, default=1000)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            account = request.args.get('account')
            logger.info(f"Processing heatmap data with min_risk={min_risk}, min_amount={min_amount}, account={account}")
            df = pd.DataFrame(data_cache.transactions)
            if len(df) == 0 or 'timestamp' not in df.columns:
                logger.error("No valid data found in dataset")
                return jsonify({
                    'error': '没有找到有效的交易数据'
                }), 404
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            if start_date and end_date:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                logger.info(f"Filtered data by date range: {len(df)} transactions")

            if account:
                logger.info(f"Filtering data for account: {account}")
                df = df[(df['nameOrig'] == account) | (df['nameDest'] == account)]
                logger.info(f"Found {len(df)} transactions for account {account}")

                if len(df) == 0:
                    logger.error(f"No transactions found for account {account}")
                    return jsonify({
                        'error': f'未找到账户 {account} 的交易记录'
                    }), 404

            high_risk_txs = df[(df['risk_score'] >= min_risk) | (df['amount'] >= min_amount)]
            logger.info(f"Found {len(high_risk_txs)} transactions matching risk criteria")

            if len(high_risk_txs) == 0:
                logger.warning("No transactions match the risk criteria")
                return jsonify({
                    'hours': [f"{h:02d}" for h in range(24)],
                    'days': ['周日', '周一', '周二', '周三', '周四', '周五', '周六'],
                    'values': [[0] * 24 for _ in range(7)],
                    'max_value': 1
                })

            high_risk_txs['weekday'] = high_risk_txs['timestamp'].dt.weekday
            high_risk_txs['hour'] = high_risk_txs['timestamp'].dt.hour

            heatmap_data = high_risk_txs.groupby(['weekday', 'hour']).agg({
                'amount': 'count',
                'risk_score': 'mean'
            }).reset_index()

            hours = list(range(24))
            days = list(range(7))
            heatmap_matrix = []
            for day in days:
                day_data = []
                for hour in hours:
                    data = heatmap_data[
                        (heatmap_data['weekday'] == day) &
                        (heatmap_data['hour'] == hour)
                        ]
                    if not data.empty:
                        count = int(data['amount'].iloc[0])
                        risk = float(data['risk_score'].iloc[0])
                        value = int(count * (1 + risk))
                    else:
                        value = 0
                    day_data.append(value)
                heatmap_matrix.append(day_data)
            day_labels = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
            hour_labels = [f"{h:02d}" for h in hours]
            max_value = max(max(row) for row in heatmap_matrix)
            if max_value == 0:
                max_value = 1
            logger.info(f"Generated heatmap data with max_value={max_value}")
            response_data = {
                'hours': hour_labels,
                'days': day_labels,
                'values': heatmap_matrix,
                'max_value': int(max_value)
            }
            return jsonify(response_data)
        except Exception as e:
            logger.error(f"Error generating heatmap data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                'error': f'生成热力图数据失败: {str(e)}'
            }), 500

    @app.route('/api/group/behavior-radar', methods=['GET'])
    def get_behavior_radar():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                logger.info("No data in cache, attempting to load data...")
                data_cache.load_data()
            df = pd.DataFrame(data_cache.transactions)
            if len(df) == 0:
                logger.warning("No transactions found in data cache")
                return jsonify({
                    'dimensions': ['交易频率', '交易金额', '交易多样性', '风险评分', '关联账户'],
                    'values': [0, 0, 0, 0, 0],
                    'stats_info': {
                        '交易频率': '0笔/天',
                        '总交易额': '¥0.00',
                        '平均金额': '¥0.00',
                        '最大金额': '¥0.00',
                        '关联账户': '0个',
                        '风险评分': '0.00'
                    }
                })
            account = request.args.get('account')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if start_date and end_date:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                logger.info(f"Filtered data by date range: {len(df)} transactions")
            if account:
                logger.info(f"Analyzing account: {account}")
                user_txs = df[(df['nameOrig'] == account) | (df['nameDest'] == account)]
                logger.info(f"Found {len(user_txs)} transactions for account {account}")
                if len(user_txs) == 0:
                    return jsonify({
                        'dimensions': ['交易频率', '交易金额', '交易多样性', '风险评分', '关联账户'],
                        'values': [0, 0, 0, 0, 0],
                        'stats_info': {
                            '交易频率': '0笔/天',
                            '总交易额': '¥0.00',
                            '平均金额': '¥0.00',
                            '最大金额': '¥0.00',
                            '关联账户': '0个',
                            '风险评分': '0.00'
                        }
                    })
                date_range = (user_txs['timestamp'].max() - user_txs['timestamp'].min()).days + 1
                days_active = max(date_range, 1)
                daily_tx_counts = user_txs.groupby(user_txs['timestamp'].dt.date).size()
                avg_daily_freq = daily_tx_counts.mean()
                max_daily_freq = daily_tx_counts.max()
                direct_contacts = set()
                for idx, row in user_txs.iterrows():
                    if row['nameOrig'] != account:
                        direct_contacts.add(row['nameOrig'])
                    if row['nameDest'] != account:
                        direct_contacts.add(row['nameDest'])
                total_amount = user_txs['amount'].sum()
                avg_amount = user_txs['amount'].mean()
                max_amount = user_txs['amount'].max()
                normalized_stats = {
                    '交易频率': min(max_daily_freq * 10, 100),
                    '交易金额': min(total_amount / 100000, 100),
                    '交易多样性': len(user_txs['type'].unique()) / 4 * 100,  #
                    '风险评分': user_txs['risk_score'].mean() * 100,
                    '关联账户': min(len(direct_contacts), 100)
                }
                stats_info = {
                    '交易频率': f"{int(avg_daily_freq)}笔/天 (最高{int(max_daily_freq)}笔)",
                    '总交易额': f"¥{total_amount:,.2f}",
                    '平均金额': f"¥{avg_amount:,.2f}",
                    '最大金额': f"¥{max_amount:,.2f}",
                    '关联账户': f"{len(direct_contacts)}个",
                    '风险评分': f"{user_txs['risk_score'].mean():.2f}"
                }
            else:
                min_risk = request.args.get('min_risk', type=float, default=0.7)
                min_amount = request.args.get('min_amount', type=float, default=10000)
                high_risk_txs = df[
                    (df['risk_score'] >= min_risk) &
                    (df['amount'] >= min_amount)
                    ]
                if len(high_risk_txs) == 0:
                    # 如果没有高风险交易，降低风险阈值
                    min_risk = min_risk * 0.8
                    min_amount = min_amount * 0.8
                    high_risk_txs = df[
                        (df['risk_score'] >= min_risk) &
                        (df['amount'] >= min_amount)
                        ]
                daily_tx_counts = high_risk_txs.groupby(high_risk_txs['timestamp'].dt.date).size()
                avg_daily_freq = daily_tx_counts.mean() if not pd.isna(daily_tx_counts.mean()) else 0
                max_daily_freq = daily_tx_counts.max() if not pd.isna(daily_tx_counts.max()) else 0
                all_accounts = set(high_risk_txs['nameOrig']) | set(high_risk_txs['nameDest'])
                total_amount = high_risk_txs['amount'].sum() if not pd.isna(high_risk_txs['amount'].sum()) else 0
                avg_amount = high_risk_txs['amount'].mean() if not pd.isna(high_risk_txs['amount'].mean()) else 0
                max_amount = high_risk_txs['amount'].max() if not pd.isna(high_risk_txs['amount'].max()) else 0
                normalized_stats = {
                    '交易频率': min(max_daily_freq * 10, 100) if not pd.isna(max_daily_freq) else 0,  # 每日最大交易次数 * 10
                    '交易金额': min(total_amount / 1000000, 100) if not pd.isna(total_amount) else 0,  # 总交易金额（以100万为基准）
                    '风险程度': high_risk_txs['risk_score'].mean() * 100 if not pd.isna(
                        high_risk_txs['risk_score'].mean()) else 0,
                    '关联账户': min(len(all_accounts), 100),  # 关联账户数量
                    '交易类型': len(high_risk_txs['type'].unique()) / 4 * 100 if len(high_risk_txs) > 0 else 0
                }
                stats_info = {
                    '交易频率': f"{int(avg_daily_freq)}笔/天 (最高{int(max_daily_freq)}笔)",
                    '总交易额': f"¥{total_amount:,.2f}",
                    '平均金额': f"¥{avg_amount:,.2f}",
                    '最大金额': f"¥{max_amount:,.2f}",
                    '关联账户': f"{len(all_accounts)}个",
                    '风险评分': f"{high_risk_txs['risk_score'].mean():.2f}" if not pd.isna(
                        high_risk_txs['risk_score'].mean()) else "0.00"
                }
            radar_data = {
                'dimensions': list(normalized_stats.keys()),
                'values': [round(v, 1) for v in normalized_stats.values()],  # 保留1位小数
                'stats_info': stats_info
            }
            logger.info(f"Returning radar data: {radar_data}")
            return jsonify(radar_data)
        except Exception as e:
            logger.error(f"Error generating behavior radar data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                'error': f'生成行为雷达图数据失败: {str(e)}'
            }), 500

    @app.route('/api/group/random-accounts', methods=['GET'])
    def get_random_accounts():
        try:
            if not data_cache.transactions or not data_cache.last_update:
                logger.info("No data in cache, attempting to load data...")
                data_cache.load_data()
            df = pd.DataFrame(data_cache.transactions)
            if len(df) == 0:
                logger.warning("No transactions found in the dataset")
                return jsonify({
                    'error': '数据集中没有交易记录'
                }), 404
            customer_accounts = df[~df['nameOrig'].str.startswith('M')]['nameOrig'].unique()
            if len(customer_accounts) == 0:
                logger.warning("No customer accounts found in the dataset")
                return jsonify({
                    'error': '未找到客户账户'
                }), 404
            selected_accounts = np.random.choice(customer_accounts, min(10, len(customer_accounts)), replace=False)
            logger.info(f"Selected {len(selected_accounts)} random accounts")
            return jsonify(selected_accounts.tolist())
        except FileNotFoundError as e:
            logger.error(f"Data file not found: {e}")
            return jsonify({
                'error': '数据文件不存在，请确保数据文件已正确放置'
            }), 404
        except Exception as e:
            logger.error(f"Error getting random accounts: {e}")
            return jsonify({
                'error': f'获取随机账户失败: {str(e)}'
            }), 500 