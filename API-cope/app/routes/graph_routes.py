from flask import jsonify, request
from app.utils.logger import logger
import networkx as nx
import time
import pandas as pd
from datetime import datetime, timedelta
import math
from app.utils.optimize import optimize_fraud_detection_response
from app.models.gnn_utils import GNNModel

def register_graph_routes(app, data_cache):
    @app.route('/api/graph/analysis/path', methods=['POST', 'OPTIONS'])
    def analyze_path():
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            return response

        try:
            logger.info("Starting path analysis...")

            data = request.get_json()
            if not data:
                logger.error("No JSON data received")
                return jsonify({
                    'error': 'No data provided',
                    'detail': {'message': '请求数据为空'}
                }), 400

            start_time = data.get('start_time')
            end_time = data.get('end_time')
            max_transactions = data.get('max_transactions', 10000)
            use_gnn = data.get('use_gnn', True)
            disable_optimization = data.get('disable_optimization', False)

            total_start_time = time.time()

            try:
                if not data_cache.transactions:
                    logger.info("Loading data cache...")
                    data_cache.load_data()

                if not data_cache.transactions:
                    logger.error("No transactions data available")
                    return jsonify({
                        'error': 'No data available',
                        'detail': {'message': '没有可用的交易数据'}
                    }), 500

                df = pd.DataFrame(data_cache.transactions)
                logger.info(f"Loaded {len(df)} transactions")

            except Exception as e:
                logger.error(f"Error loading data: {str(e)}")
                return jsonify({
                    'error': 'Data loading failed',
                    'detail': {'message': '数据加载失败'}
                }), 500

            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                if start_time and end_time:
                    try:
                        start = pd.to_datetime(start_time)
                        end = pd.to_datetime(end_time)
                        df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                        logger.info(f"Filtered to {len(df)} transactions between {start} and {end}")
                    except Exception as e:
                        logger.error(f"Error parsing date range: {str(e)}")
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=30)
                        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                        logger.info(f"Using default date range: {len(df)} transactions between {start_date} and {end_date}")

                if len(df) > max_transactions:
                    logger.warning(f"Limiting analysis to {max_transactions} transactions")
                    
                    # 1. 保留所有高风险交易（风险分数 >= 0.7）
                    high_risk_df = df[df['risk_score'] >= 0.7]
                    remaining_df = df[df['risk_score'] < 0.7]
                    
                    # 2. 如果高风险交易数量已经超过限制，只保留风险分数最高的部分
                    if len(high_risk_df) > max_transactions:
                        high_risk_df = high_risk_df.sort_values(['risk_score', 'amount'], ascending=[False, False]).head(max_transactions)
                        df = high_risk_df
                    else:
                        # 3. 在剩余空间中，按风险分数和时间戳排序选择其他交易
                        remaining_slots = max_transactions - len(high_risk_df)
                        if remaining_slots > 0:
                            # 优先选择最近的可疑交易（风险分数 >= 0.4）
                            suspicious_df = remaining_df[remaining_df['risk_score'] >= 0.4]
                            normal_df = remaining_df[remaining_df['risk_score'] < 0.4]
                            
                            suspicious_sample_size = min(len(suspicious_df), int(remaining_slots * 0.7))  # 70%给可疑交易
                            normal_sample_size = remaining_slots - suspicious_sample_size
                            
                            sampled_suspicious = suspicious_df.sort_values(['risk_score', 'timestamp'], ascending=[False, False]).head(suspicious_sample_size)
                            sampled_normal = normal_df.sample(n=min(len(normal_df), normal_sample_size))  # 随机采样普通交易
                            
                            # 合并所有采样结果
                            df = pd.concat([high_risk_df, sampled_suspicious, sampled_normal])
                    
                    logger.info(f"Sampled {len(df)} transactions: {len(high_risk_df)} high risk, {len(df) - len(high_risk_df)} other")

                if len(df) == 0:
                    logger.warning("No transactions found after filtering")
                    return jsonify({
                        'paths': [],
                        'nodes': [],
                        'edges': []
                    })

            except Exception as e:
                logger.error(f"Error preprocessing data: {str(e)}")
                return jsonify({
                    'error': 'Data preprocessing failed',
                    'detail': {'message': '数据预处理失败'}
                }), 500

            try:
                G = nx.DiGraph()

                for _, row in df.iterrows():
                    source = str(row['nameOrig'])
                    target = str(row['nameDest'])
                    amount = float(row.get('amount', 0))
                    risk_score = float(row.get('risk_score', 0))

                    G.add_edge(source, target,
                               weight=amount,
                               risk_score=risk_score)

                logger.info(f"Built graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

                if use_gnn and data_cache.gnn_model is not None:
                    try:
                        logger.info("Enhancing graph with GNN model...")
                        pyg_data, G = data_cache.gnn_model.prepare_graph_data(df, G)
                        embeddings = data_cache.gnn_model.compute_embeddings(pyg_data)
                        risk_scores = data_cache.gnn_model.predict_node_risks(pyg_data)
                        potential_edges = data_cache.gnn_model.predict_potential_edges(pyg_data, G, threshold=0.65)
                        gnn_clusters = data_cache.gnn_model.cluster_similar_nodes(min_samples=3, eps=0.4)
                        G = data_cache.gnn_model.enhance_graph(G)
                        logger.info("Graph enhanced with GNN model")
                    except Exception as e:
                        logger.error(f"Error enhancing graph with GNN: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())

            except Exception as e:
                logger.error(f"Error building graph: {str(e)}")
                return jsonify({
                    'error': 'Graph building failed',
                    'detail': {'message': '网络构建失败'}
                }), 500

            try:
                path_analysis_start = time.time()

                high_risk_nodes = []

                if use_gnn and data_cache.gnn_model:
                    high_risk_nodes = [(node, risk) for node, risk in data_cache.gnn_model.node_risks.items() if risk > 0.7]
                    high_risk_nodes.sort(key=lambda x: x[1], reverse=True)
                    high_risk_nodes = high_risk_nodes[:20]
                else:
                    risk_scores = {}
                    for node in G.nodes():
                        out_risks = [G[node][succ].get('risk_score', 0) for succ in G.successors(node)]
                        if any(risk > 0.7 for risk in out_risks) and out_risks:
                            avg_risk = sum(out_risks) / len(out_risks)
                            risk_scores[node] = avg_risk

                    high_risk_nodes = sorted(risk_scores.items(), key=lambda x: x[1], reverse=True)[:20]

                logger.info(f"Found {len(high_risk_nodes)} high risk nodes in {time.time() - path_analysis_start:.2f} seconds")

                paths = []
                node_transactions_cache = {}

                if high_risk_nodes:
                    try:
                        pagerank_start = time.time()
                        pagerank = nx.pagerank(G, weight='weight')
                        logger.info(f"PageRank computed in {time.time() - pagerank_start:.2f} seconds")

                        important_nodes = sorted(pagerank.items(),
                                               key=lambda x: x[1],
                                               reverse=True)[:10]

                        paths_start = time.time()

                        for node, _ in important_nodes:
                            if node not in node_transactions_cache:
                                node_txs = df[(df['nameOrig'] == node) | (df['nameDest'] == node)]
                                node_transactions_cache[node] = node_txs
                            else:
                                node_txs = node_transactions_cache[node]

                            if not node_txs.empty:
                                risk_score = data_cache.gnn_model.node_risks.get(node, float(
                                    node_txs['risk_score'].mean())) if use_gnn and data_cache.gnn_model else float(
                                    node_txs['risk_score'].mean())

                                paths.append({
                                    'account_id': node,
                                    'risk_score': risk_score,
                                    'total_amount': float(node_txs['amount'].sum()),
                                    'account_type': '商户' if str(node).startswith('M') else '个人',
                                    'last_transaction': node_txs['timestamp'].max().isoformat()
                                })

                        logger.info(f"Path analysis completed in {time.time() - paths_start:.2f} seconds")

                    except Exception as e:
                        logger.error(f"Error calculating pagerank: {str(e)}")

                response_build_start = time.time()

                nodes = []
                edges = []
                node_cache = {}

                node_to_cluster = {}
                if use_gnn and data_cache.gnn_model:
                    for cluster_id, cluster_info in getattr(data_cache.gnn_model, 'gnn_clusters', {}).items():
                        for member in cluster_info.get('members', []):
                            node_to_cluster[member['node']] = cluster_id

                for node in G.nodes():
                    if node not in node_transactions_cache:
                        node_txs = df[(df['nameOrig'] == node) | (df['nameDest'] == node)]
                        node_transactions_cache[node] = node_txs
                    else:
                        node_txs = node_transactions_cache[node]

                    if not node_txs.empty:
                        risk_score = data_cache.gnn_model.node_risks.get(node, float(
                            node_txs['risk_score'].mean())) if use_gnn and data_cache.gnn_model else float(
                            node_txs['risk_score'].mean())
                        tx_count = len(node_txs)
                        total_amount = float(node_txs['amount'].sum())

                        gnn_cluster_id = node_to_cluster.get(node) if use_gnn and data_cache.gnn_model else None

                        nodes.append({
                            'id': node,
                            'name': node,
                            'value': total_amount,
                            'tx_count': tx_count,
                            'category': 0 if str(node).startswith('M') else 1,
                            'risk_score': risk_score,
                            'gnn_cluster': gnn_cluster_id,
                            'symbolSize': min(50, 20 + math.log(tx_count + 1) * 5)
                        })

                edge_limit = min(3000, G.number_of_edges())
                edge_tuples = []
                for u, v, data in G.edges(data=True):
                    is_potential = data.get('is_potential', False)
                    risk_score = float(data.get('risk_score', 0))
                    importance = risk_score * (2 if is_potential else 1)
                    edge_tuples.append((u, v, data, importance))

                edge_tuples.sort(key=lambda x: x[3], reverse=True)

                for u, v, data, _ in edge_tuples[:edge_limit]:
                    is_potential = data.get('is_potential', False)

                    edges.append({
                        'source': u,
                        'target': v,
                        'value': float(data.get('weight', 0)),
                        'risk_score': float(data.get('risk_score', 0)),
                        'is_potential': is_potential,
                        'similarity': float(data.get('similarity', 0)) if is_potential else 0
                    })

                gnn_info = {}
                if use_gnn and data_cache.gnn_model:
                    clusters_summary = {}
                    for cluster_id, cluster_data in getattr(data_cache.gnn_model, 'gnn_clusters', {}).items():
                        clusters_summary[cluster_id] = {
                            'count': cluster_data.get('count', 0),
                            'avg_risk_score': cluster_data.get('avg_risk_score', 0),
                            'risk_level': cluster_data.get('risk_level', 'low'),
                            'members': [{'node': m['node'], 'risk_score': m['risk_score']}
                                        for m in cluster_data.get('members', [])[:5]]
                        }

                    gnn_info = {
                        'clusters': clusters_summary,
                        'potential_edges_count': len(getattr(data_cache.gnn_model, 'potential_edges', [])),
                        'node_embedding_dim': len(
                            list(data_cache.gnn_model.node_embeddings.values())[0]) if data_cache.gnn_model.node_embeddings else 0
                    }

                logger.info(f"Response data prepared in {time.time() - response_build_start:.2f} seconds")

                response_data = {
                    'paths': paths,
                    'nodes': nodes,
                    'edges': edges,
                    'gnn_info': gnn_info
                }

                if not disable_optimization:
                    response_data = optimize_fraud_detection_response(paths, nodes, edges, gnn_info)

                total_time = time.time() - total_start_time
                logger.info(
                    f"Analysis complete: {len(paths)} paths, {len(nodes)} nodes, {len(edges)} edges in {total_time:.2f} seconds")

                return jsonify({
                    "result": response_data
                })

            except Exception as e:
                logger.error(f"Error in path analysis: {str(e)}")
                return jsonify({
                    'error': 'Analysis failed',
                    'detail': {'message': '路径分析失败'}
                }), 500

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                'error': 'Unexpected error',
                'detail': {'message': '服务器内部错误'}
            }), 500 