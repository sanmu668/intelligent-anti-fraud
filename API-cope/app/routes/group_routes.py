from flask import jsonify, request
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
            # Get request parameters
            min_risk = request.args.get('min_risk', type=float, default=0.5)
            min_amount = request.args.get('min_amount', type=float, default=1000)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            account = request.args.get('account')

            # Call service layer function
            result = get_group_heatmap_data(
                data_cache=data_cache,
                min_risk=min_risk,
                min_amount=min_amount,
                start_date=start_date,
                end_date=end_date,
                account=account
            )

            if 'error' in result:
                return jsonify({'error': result['error']}), 500 if '生成热力图数据失败' in result['error'] else 404
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error in heatmap route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/group/behavior-radar', methods=['GET'])
    def get_behavior_radar():
        try:
            # Get request parameters
            account = request.args.get('account')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Call service layer function
            result = get_group_behavior_radar_data(
                data_cache=data_cache,
                account=account,
                start_date=start_date,
                end_date=end_date
            )

            if 'error' in result:
                return jsonify({'error': result['error']}), 500
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error in behavior radar route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/group/random-accounts', methods=['GET'])
    def get_random_accounts():
        try:
            # Call service layer function
            result = get_random_accounts_data(data_cache)

            if 'error' in result:
                return jsonify({'error': result['error']}), 404
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error in random accounts route: {e}")
            return jsonify({'error': str(e)}), 500 