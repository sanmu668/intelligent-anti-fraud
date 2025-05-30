from flask import jsonify, request
from app.services.alert_service import get_alerts_data, process_alerts_batch
from app.utils.logger import logger

def register_alert_routes(app, data_cache):
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        try:
            # Get request parameters
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('pageSize', 20, type=int)
            alert_type = request.args.get('alertType', '')
            risk_level = request.args.get('riskLevel', '')
            status = request.args.get('status', '')
            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')

            # Call service layer function
            result = get_alerts_data(
                data_cache=data_cache,
                page=page,
                page_size=page_size,
                alert_type=alert_type,
                risk_level=risk_level,
                status=status,
                start_date=start_date,
                end_date=end_date
            )

            if 'error' in result:
                return jsonify({'error': result['error']}), 500
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error in alerts route: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/alerts/batch-process', methods=['POST'])
    def batch_process_alerts():
        try:
            # Get request data
            data = request.json
            
            # Call service layer function
            result = process_alerts_batch(data)
            
            if 'error' in result:
                return jsonify({'error': result['error']}), 500
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error in batch process route: {e}")
            return jsonify({'error': str(e)}), 500 