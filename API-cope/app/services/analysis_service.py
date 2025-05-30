import pandas as pd
from datetime import datetime
from app.utils.logger import logger

def get_analysis_trends_data(data_cache, trend_type='week', start_date=None, end_date=None):
    """Get analysis trends data"""
    try:
        if not data_cache.transactions or not data_cache.last_update:
            logger.info("Loading data cache...")
            data_cache.load_data()

        df = pd.DataFrame(data_cache.transactions)
        if len(df) == 0 or 'timestamp' not in df.columns:
            logger.error("No valid data found in dataset")
            return {
                'error': '没有找到有效的交易数据'
            }

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        if start_date and end_date:
            try:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                logger.info(f"Filtered data by date range: {len(df)} transactions")
                
                if len(df) == 0:
                    logger.warning("No data found in the specified date range")
                    return {
                        'error': '在指定日期范围内没有找到交易数据'
                    }
            except Exception as e:
                logger.error(f"Error parsing dates: {e}")
                return {
                    'error': f'Invalid date format: {str(e)}'
                }

        if trend_type == 'week':
            df['time_group'] = df['timestamp'].dt.strftime('%Y-%m-%d')
            time_format = '%m-%d'
        elif trend_type == 'month':
            df['time_group'] = df['timestamp'].dt.strftime('%Y-%m')
            time_format = '%Y-%m'
        else:
            logger.error(f"Invalid trend type: {trend_type}")
            return {
                'error': f'不支持的趋势类型: {trend_type}'
            }

        daily_stats = df.groupby('time_group').agg({
            'amount': 'count',
            'risk_score': lambda x: (
                sum(x > 0.8),  # 高风险
                sum((x > 0.6) & (x <= 0.8)),  # 可疑
                len(x)  # 总数
            )
        }).reset_index()

        if len(daily_stats) == 0:
            logger.warning("No statistics data generated")
            return {
                'xAxis': [],
                'series': [
                    {
                        'name': '高风险交易',
                        'type': 'line',
                        'data': [],
                        'itemStyle': {'color': '#F56C6C'}
                    },
                    {
                        'name': '可疑交易',
                        'type': 'line',
                        'data': [],
                        'itemStyle': {'color': '#E6A23C'}
                    },
                    {
                        'name': '总交易量',
                        'type': 'line',
                        'data': [],
                        'itemStyle': {'color': '#409EFF'}
                    }
                ]
            }

        dates = daily_stats['time_group'].tolist()
        high_risk = [int(x[0]) for x in daily_stats['risk_score']]
        suspicious = [int(x[1]) for x in daily_stats['risk_score']]
        total = [int(x) for x in daily_stats['amount']]

        logger.info(f"Generated trends data with {len(dates)} time points")
        return {
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
        }
    except Exception as e:
        logger.error(f"Error generating analysis trends data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'error': f'生成趋势分析数据失败: {str(e)}'} 