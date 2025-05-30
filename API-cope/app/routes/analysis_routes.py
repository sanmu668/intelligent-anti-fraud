from flask import jsonify, request
from app.services.analysis_service import get_analysis_trends_data
from app.utils.logger import logger

def register_analysis_routes(app, data_cache):
    @app.route('/api/analysis/trends', methods=['GET'])
    def get_analysis_trends():
        try:
            # Get request parameters
            trend_type = request.args.get('type', 'week')
            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')

            # Call service layer function
            result = get_analysis_trends_data(
                data_cache=data_cache,
                trend_type=trend_type,
                start_date=start_date,
                end_date=end_date
            )

            if 'error' in result:
                return jsonify({'error': result['error']}), 500 if '生成趋势分析数据失败' in result['error'] else 404
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error in analysis trends route: {e}")
            return jsonify({'error': str(e)}), 500 