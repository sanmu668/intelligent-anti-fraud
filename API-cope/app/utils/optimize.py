def optimize_fraud_detection_response(paths, nodes, edges, gnn_info):
    """
    为诈骗检测项目优化响应数据
    保留高风险信息同时减少数据量
    """
    high_risk_threshold = 0.6
    high_risk_nodes = {node['id'] for node in nodes if node.get('risk_score', 0) >= high_risk_threshold}
    connected_nodes = set()
    second_degree = set()
    for edge in edges:
        if edge['source'] in high_risk_nodes:
            connected_nodes.add(edge['target'])
        if edge['target'] in high_risk_nodes:
            connected_nodes.add(edge['source'])

    for edge in edges:
        if edge['source'] in connected_nodes and edge['target'] not in high_risk_nodes:
            second_degree.add(edge['target'])
        if edge['target'] in connected_nodes and edge['source'] not in high_risk_nodes:
            second_degree.add(edge['source'])

    nodes_to_keep = high_risk_nodes.union(connected_nodes).union(second_degree)

    low_risk_nodes = {node['id'] for node in nodes
                      if node['id'] not in nodes_to_keep
                      and node.get('risk_score', 0) < high_risk_threshold}

    category_groups = {}
    for node in nodes:
        if node['id'] in low_risk_nodes:
            category = node.get('category', 0)
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(node)

    aggregated_nodes = []
    for category, node_list in category_groups.items():
        if len(node_list) > 5:  # 只聚合数量足够多的节点
            agg_value = sum(node.get('value', 0) for node in node_list)
            avg_risk = sum(node.get('risk_score', 0) for node in node_list) / len(node_list)

            aggregated_nodes.append({
                'id': f"agg_cat_{category}",
                'name': f"{'商户' if category == 0 else '个人'} 群组",
                'value': agg_value,
                'tx_count': sum(node.get('tx_count', 0) for node in node_list),
                'category': category,
                'risk_score': avg_risk,
                'symbolSize': 35,  # 稍大的尺寸表示聚合节点
                'is_aggregated': True,
                'node_count': len(node_list)
            })
        else:
            aggregated_nodes.extend(node_list)

    for node in nodes:
        if node['id'] in nodes_to_keep:
            optimized_node = {
                'id': node['id'],
                'name': node.get('name', node['id']),
                'value': node.get('value', 0),
                'tx_count': node.get('tx_count', 0),
                'category': node.get('category', 0),
                'risk_score': round(node.get('risk_score', 0), 4),  # 保留4位小数的精度
                'symbolSize': node.get('symbolSize', 25),
            }

            if node.get('gnn_cluster') is not None:
                optimized_node['gnn_cluster'] = node['gnn_cluster']
            aggregated_nodes.append(optimized_node)

    optimized_edges = []
    node_ids = {node['id'] for node in aggregated_nodes}
    edge_map = {}
    for edge in edges:
        source = edge['source']
        target = edge['target']
        source_in_agg = source in node_ids
        target_in_agg = target in node_ids
        if not source_in_agg and not target_in_agg:
            continue
        if source in high_risk_nodes or target in high_risk_nodes:
            optimized_edges.append({
                'source': source,
                'target': target,
                'value': edge.get('value', 0),
                'risk_score': round(edge.get('risk_score', 0), 4),
                'is_potential': edge.get('is_potential', False)
            })
        else:
            source_node = next((n for n in aggregated_nodes if n['id'] == source), None)
            target_node = next((n for n in aggregated_nodes if n['id'] == target), None)
            if source_node and target_node:
                edge_key = f"{source}_{target}"
                if edge_key not in edge_map:
                    edge_map[edge_key] = {
                        'source': source,
                        'target': target,
                        'value': 0,
                        'risk_score': 0,
                        'transaction_count': 0
                    }
                edge_map[edge_key]['value'] += edge.get('value', 0)
                edge_map[edge_key]['risk_score'] = max(edge_map[edge_key]['risk_score'], edge.get('risk_score', 0))
                edge_map[edge_key]['transaction_count'] += 1
    for edge_data in edge_map.values():
        optimized_edges.append({
            'source': edge_data['source'],
            'target': edge_data['target'],
            'value': edge_data['value'],
            'risk_score': round(edge_data['risk_score'], 4),
            'transaction_count': edge_data['transaction_count']
        })
    optimized_paths = []
    for path in paths:
        optimized_paths.append({
            'account_id': path.get('account_id', ''),
            'risk_score': round(path.get('risk_score', 0), 4),
            'total_amount': path.get('total_amount', 0),
            'account_type': path.get('account_type', '未知'),
            'last_transaction': path.get('last_transaction', '')
        })
    optimized_gnn_info = {}
    if gnn_info:
        clusters = {}
        for cluster_id, cluster_data in gnn_info.get('clusters', {}).items():
            if cluster_data.get('avg_risk_score', 0) >= 0.5:
                clusters[cluster_id] = {
                    'count': cluster_data.get('count', 0),
                    'avg_risk_score': round(cluster_data.get('avg_risk_score', 0), 4),
                    'risk_level': cluster_data.get('risk_level', 'low'),
                    'members': cluster_data.get('members', [])[:3]
                }
        optimized_gnn_info = {
            'clusters': clusters,
            'potential_edges_count': gnn_info.get('potential_edges_count', 0)
        }
    return {
        'paths': optimized_paths,
        'nodes': aggregated_nodes,
        'edges': optimized_edges,
        'gnn_info': optimized_gnn_info,
        'optimization_info': {
            'original_node_count': len(nodes),
            'optimized_node_count': len(aggregated_nodes),
            'original_edge_count': len(edges),
            'optimized_edge_count': len(optimized_edges),
            'high_risk_node_count': len(high_risk_nodes)
        }
    } 