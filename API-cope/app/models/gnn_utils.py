import os
import logging
import torch
import numpy as np
import networkx as nx
import math
import time
import traceback
from ..config.config import Config

try:
    from torch_geometric.data import Data
    from torch_geometric.transforms import NormalizeFeatures
    PYG_AVAILABLE = True
except ImportError:
    class Data:
        def __init__(self, x, edge_index, edge_attr=None):
            self.x = x
            self.edge_index = edge_index
            self.edge_attr = edge_attr
        def to(self, device):
            self.x = self.x.to(device)
            self.edge_index = self.edge_index.to(device)
            if self.edge_attr is not None:
                self.edge_attr = self.edge_attr.to(device)
            return self
    class NormalizeFeatures:
        def __call__(self, data):
            x = data.x
            mean = torch.mean(x, dim=0, keepdim=True)
            std = torch.std(x, dim=0, keepdim=True)
            data.x = (x - mean) / (std + 1e-5)
            return data
    PYG_AVAILABLE = False
    logging.warning("PyTorch Geometric not available, using fallback implementations")
try:
    from sklearn.cluster import DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    class DBSCAN:
        def __init__(self, eps=0.5, min_samples=5):
            self.eps = eps
            self.min_samples = min_samples
        def fit_predict(self, X):
            n = len(X)
            dist_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(i+1, n):
                    dist = np.sqrt(np.sum((X[i] - X[j]) ** 2))
                    dist_matrix[i, j] = dist
                    dist_matrix[j, i] = dist
            neighbors = []
            for i in range(n):
                neighbors.append(np.where(dist_matrix[i] < self.eps)[0])
            labels = np.full(n, -1)
            cluster_id = 0
            for i in range(n):
                if labels[i] != -1:
                    continue
                if len(neighbors[i]) >= self.min_samples:
                    labels[i] = cluster_id
                    stack = list(neighbors[i])
                    while stack:
                        j = stack.pop(0)
                        if labels[j] == -1:
                            labels[j] = cluster_id
                            if len(neighbors[j]) >= self.min_samples:
                                stack.extend([x for x in neighbors[j] if labels[x] == -1])
                    cluster_id += 1
            return labels
            
    def cosine_similarity(X):
        norm = np.sqrt(np.sum(X * X, axis=1))
        norm = norm.reshape(-1, 1)
        norm[norm == 0] = 1
        X_normalized = X / norm
        return np.dot(X_normalized, X_normalized.T)
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available, using simplified clustering implementation")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GNNModel:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = Config.GNN_MODEL_PATH
            
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024  # GB
            logger.info(f"CUDA available! Using GPU: {gpu_name} with {gpu_mem:.2f} GB memory")
            torch.cuda.empty_cache()
            torch.backends.cudnn.benchmark = True
            try:
                self.device = torch.device('cuda')
            except Exception as e:
                logger.warning(f"Failed to set device to cuda: {e}. Using CPU instead.")
                self.device = torch.device('cpu')
        else:
            logger.warning("CUDA not available. Using CPU instead. This will be significantly slower.")
            self.device = torch.device('cpu')
            
        logger.info(f"Using device: {self.device}")
        if self.device.type == 'cuda':
            torch.set_default_tensor_type('torch.cuda.FloatTensor')
        else:
            torch.set_default_tensor_type('torch.FloatTensor')

        self.model = None
        self.model_type = None
        success = False
        
        try:
            logger.info(f"Trying to load GNN model from: {model_path}")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model path does not exist: {model_path}")
                
            if model_path.endswith('.pth'):
                # 尝试加载PyTorch模型
                model_data = torch.load(model_path, map_location=self.device)
                if isinstance(model_data, dict) and 'state_dict' in model_data:
                    # 如果是模型状态字典
                    self.model = self._create_gnn_model()
                    self.model.load_state_dict(model_data['state_dict'])
                    self.model_type = 'gnn'
                elif isinstance(model_data, torch.nn.Module):
                    # 如果是完整的模型
                    self.model = model_data
                    self.model_type = 'gnn'
                else:
                    # 如果是其他类型的数据
                    logger.warning("Model file contains unexpected data type, creating wrapper")
                    self.model = self._create_model_wrapper(model_data)
                    self.model_type = 'wrapper'
                
                self.model = self.model.to(self.device)
                self.model.eval()
                success = True
                
            elif model_path.endswith('.pkl'):
                # 尝试加载scikit-learn模型
                import pickle
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.model_type = 'sklearn'
                success = True
                
            if success:
                logger.info(f"Successfully loaded model type: {self.model_type}")
                if self.device.type == 'cuda' and hasattr(torch, 'amp'):
                    self.use_amp = True
                    logger.info("Enabling mixed precision for faster inference")
                else:
                    self.use_amp = False
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.error(traceback.format_exc())
            self.model = self._create_dummy_model()
            self.model_type = 'dummy'
            self.use_amp = False
            
        self.node_embeddings = {}
        self.node_risks = {}
        self.potential_edges = []
        self.batch_size = 1024 if self.device.type == 'cuda' else 256

    def _create_gnn_model(self):
        """创建GNN模型结构"""
        class GNN(torch.nn.Module):
            def __init__(self, input_dim=6, hidden_dim=32, output_dim=1):
                super().__init__()
                self.conv1 = torch.nn.Linear(input_dim, hidden_dim)
                self.conv2 = torch.nn.Linear(hidden_dim, hidden_dim)
                self.conv3 = torch.nn.Linear(hidden_dim, output_dim)
                
            def forward(self, data):
                x = data.x
                x = torch.relu(self.conv1(x))
                x = torch.relu(self.conv2(x))
                x = self.conv3(x)
                return x.squeeze(-1)
                
        return GNN()

    def _create_model_wrapper(self, data):
        """为非标准模型创建包装器"""
        class ModelWrapper(torch.nn.Module):
            def __init__(self, data):
                super().__init__()
                if isinstance(data, np.ndarray):
                    self.data = torch.nn.Parameter(torch.from_numpy(data).float())
                else:
                    self.data = torch.nn.Parameter(torch.tensor(data).float())
                    
            def forward(self, x):
                return self.data
                
        return ModelWrapper(data)

    def _create_dummy_model(self):
        """创建一个简单的备用模型"""
        class DummyModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.randn(1))
                self.embedding_dim = 32
                
            def forward(self, data):
                x = data.x
                return torch.sigmoid(x.sum(dim=1) * self.weight)
                
            def get_embeddings(self, data):
                x = data.x
                # 创建一个简单的嵌入：将输入特征转换为固定维度
                if x.shape[1] > self.embedding_dim:
                    return x[:, :self.embedding_dim]
                else:
                    padding = torch.zeros(x.shape[0], self.embedding_dim - x.shape[1], device=x.device)
                    return torch.cat([x, padding], dim=1)
                
        return DummyModel()

    def prepare_graph_data(self, df, G=None):
        if G is None:
            G = nx.DiGraph()
            for _, row in df.iterrows():
                source = str(row['nameOrig'])
                target = str(row['nameDest'])
                amount = float(row['amount'])
                risk = float(row.get('risk_score', 0))
                G.add_edge(source, target, weight=amount, risk_score=risk)
        node_map = {node: i for i, node in enumerate(G.nodes())}
        edge_index = []
        edge_attr = []
        for u, v, data in G.edges(data=True):
            edge_index.append([node_map[u], node_map[v]])
            edge_attr.append([data.get('weight', 0), data.get('risk_score', 0)])
        x = []
        for node in G.nodes():
            node_data = G.nodes[node]
            features = [
                node_data.get('transaction_count', 0),
                node_data.get('total_amount', 0),
                node_data.get('risk_score', 0),
                1 if str(node).startswith('M') else 0,
                G.in_degree(node),
                G.out_degree(node)
            ]
            x.append(features)
        x = torch.tensor(x, dtype=torch.float)
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        edge_attr = torch.tensor(edge_attr, dtype=torch.float)
        data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
        transform = NormalizeFeatures()
        data = transform(data)
        self.node_map = node_map
        self.reverse_map = {i: node for node, i in node_map.items()}
        return data, G
    
    def compute_embeddings(self, data):
        if self.model is None:
            logger.error("GNN model not loaded, cannot compute embeddings")
            random_embeddings = np.random.rand(len(self.reverse_map), 16)
            for i, node_id in self.reverse_map.items():
                self.node_embeddings[node_id] = random_embeddings[i]
            logger.warning("Using random embeddings as fallback")
            return random_embeddings
        try:
            start_time = time.time()
            num_nodes = data.x.size(0)
            logger.info(f"Computing embeddings for {num_nodes} nodes using batch size {self.batch_size}")
            all_embeddings = None
            with torch.no_grad():
                for i in range(0, num_nodes, self.batch_size):
                    end_idx = min(i + self.batch_size, num_nodes)
                    batch_indices = torch.arange(i, end_idx, device=self.device)
                    batch_mask = torch.zeros(num_nodes, dtype=torch.bool, device=self.device)
                    batch_mask[batch_indices] = True
                    batch_data = data.to(self.device)
                    try:
                        if self.use_amp and hasattr(torch.cuda, 'amp'):
                            with torch.cuda.amp.autocast():
                                try:
                                    batch_embeddings = self.model.get_embeddings(batch_data)
                                except (AttributeError, Exception) as e:
                                    logger.warning(f"Model get_embeddings failed: {e}, using node features instead")
                                    batch_embeddings = batch_data.x
                        else:
                            try:
                                batch_embeddings = self.model.get_embeddings(batch_data)
                            except (AttributeError, Exception) as e:
                                logger.warning(f"Model get_embeddings failed: {e}, using node features instead")
                                batch_embeddings = batch_data.x
                        if batch_embeddings.device != batch_indices.device:
                            logger.info(f"Moving batch_embeddings from {batch_embeddings.device} to {batch_indices.device}")
                            batch_embeddings = batch_embeddings.to(batch_indices.device)
                        batch_embeddings = batch_embeddings[batch_indices]
                        batch_embeddings_np = batch_embeddings.cpu().numpy()
                        if all_embeddings is None:
                            embedding_dim = batch_embeddings_np.shape[1]
                            all_embeddings = np.zeros((num_nodes, embedding_dim), dtype=np.float32)
                        all_embeddings[i:end_idx] = batch_embeddings_np
                        if (i // self.batch_size) % 5 == 0:
                            progress = (end_idx / num_nodes) * 100
                            logger.info(f"Computing embeddings: {progress:.1f}% complete")
                    except Exception as e:
                        logger.error(f"Error in batch {i}-{end_idx}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        if all_embeddings is not None:
                            all_embeddings[i:end_idx] = 0
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()
                for i, embedding in enumerate(all_embeddings):
                    node_id = self.reverse_map[i]
                    self.node_embeddings[node_id] = embedding
                compute_time = time.time() - start_time
                logger.info(f"Computed embeddings for {num_nodes} nodes in {compute_time:.2f} seconds")
                return all_embeddings
        except Exception as e:
            logger.error(f"Error computing embeddings: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 创建随机嵌入作为回退
            random_embeddings = np.random.rand(len(self.reverse_map), 16)  # 16维随机嵌入
            for i, node_id in self.reverse_map.items():
                self.node_embeddings[node_id] = random_embeddings[i]
            logger.warning("Using random embeddings as fallback after error")
            return random_embeddings
    def predict_node_risks(self, data):
        if self.model is None:
            logger.error("Model not loaded, cannot predict risks")
            return self._fallback_risk_calculation(data)
            
        try:
            start_time = time.time()
            num_nodes = data.x.size(0)
            logger.info(f"Predicting risks for {num_nodes} nodes using batch size {self.batch_size}")
            all_risk_scores = np.zeros(num_nodes, dtype=np.float32)
            
            with torch.no_grad():
                for i in range(0, num_nodes, self.batch_size):
                    end_idx = min(i + self.batch_size, num_nodes)
                    batch_indices = torch.arange(i, end_idx).to(self.device)
                    batch_data = data.to(self.device)
                    
                    try:
                        if self.model_type == 'gnn':
                            # GNN模型直接处理图数据
                            batch_scores = self.model(batch_data)
                            batch_scores = torch.sigmoid(batch_scores)
                        elif self.model_type == 'sklearn':
                            # scikit-learn模型处理特征
                            features = batch_data.x.cpu().numpy()
                            if hasattr(self.model, 'predict_proba'):
                                batch_scores = self.model.predict_proba(features)[:, 1]
                            else:
                                batch_scores = self.model.predict(features)
                            batch_scores = torch.from_numpy(batch_scores).float().to(self.device)
                        else:
                            # 其他类型模型
                            batch_scores = self.model(batch_data)
                            if isinstance(batch_scores, np.ndarray):
                                batch_scores = torch.from_numpy(batch_scores).float()
                            batch_scores = torch.sigmoid(batch_scores)
                            
                        batch_scores = batch_scores.to(self.device)
                        batch_scores = batch_scores[batch_indices]
                        all_risk_scores[i:end_idx] = batch_scores.cpu().numpy()
                        
                        if (i // self.batch_size) % 5 == 0:
                            progress = (end_idx / num_nodes) * 100
                            logger.info(f"Predicting risks: {progress:.1f}% complete")
                            
                    except Exception as e:
                        logger.error(f"Error in batch {i}-{end_idx}: {e}")
                        logger.error(traceback.format_exc())
                        all_risk_scores[i:end_idx] = self._fallback_risk_calculation_batch(batch_data, batch_indices)

            # 更新节点风险分数
            high_risk_count = 0
            for i, risk in enumerate(all_risk_scores):
                node_id = self.reverse_map[i]
                self.node_risks[node_id] = float(risk)
                if risk >= Config.HIGH_RISK_THRESHOLD:
                    high_risk_count += 1

            compute_time = time.time() - start_time
            logger.info(f"Predicted risks for {num_nodes} nodes in {compute_time:.2f} seconds")
            logger.info(f"Found {high_risk_count} high risk nodes (risk >= {Config.HIGH_RISK_THRESHOLD})")
            return all_risk_scores
            
        except Exception as e:
            logger.error(f"Error predicting node risks: {e}")
            logger.error(traceback.format_exc())
            return self._fallback_risk_calculation(data)
    
    def _fallback_risk_calculation(self, data):
        logger.warning("Using fallback risk calculation based on node features")
        features = data.x.cpu().numpy()
        node_risks = []
        for i, feat in enumerate(features):
            transaction_count = float(feat[0])
            total_amount = float(feat[1])
            base_risk = float(feat[2])
            is_merchant = bool(feat[3])
            in_degree = int(feat[4])
            out_degree = int(feat[5])
            risk = base_risk
            if total_amount > 1000000:
                risk += 0.2
            if in_degree > 0 and out_degree > 0:
                ratio = out_degree / in_degree
                if ratio > 5 or ratio < 0.2:  # 出入比例不平衡
                    risk += 0.15
            if transaction_count > 100:
                risk += 0.1
            risk = min(risk, 1.0)
            node_id = self.reverse_map[i]
            self.node_risks[node_id] = float(risk)
            node_risks.append(risk)
        return np.array(node_risks)
    def _fallback_risk_calculation_batch(self, data, batch_indices):
        logger.warning(f"Using fallback risk calculation for batch of {len(batch_indices)} nodes")
        features = data.x[batch_indices].cpu().numpy()
        batch_risks = np.zeros(len(batch_indices), dtype=np.float32)
        for j, feat in enumerate(features):
            i = batch_indices[j].item()
            transaction_count = float(feat[0])
            total_amount = float(feat[1])
            base_risk = float(feat[2])
            is_merchant = bool(feat[3])
            in_degree = int(feat[4])
            out_degree = int(feat[5])
            risk = base_risk
            if total_amount > 1000000:
                risk += 0.2
            if in_degree > 0 and out_degree > 0:
                ratio = out_degree / in_degree
                if ratio > 5 or ratio < 0.2:  # 出入比例不平衡
                    risk += 0.15
            if transaction_count > 100:
                risk += 0.1
            risk = min(risk, 1.0)
            node_id = self.reverse_map[i]
            self.node_risks[node_id] = float(risk)
            batch_risks[j] = risk
        return batch_risks
    def predict_potential_edges(self, data, G, threshold=0.7):
        if not self.node_embeddings:
            logger.error("Node embeddings not computed")
            return self._fallback_potential_edges(G)
            
        try:
            start_time = time.time()
            nodes = list(G.nodes())
            if not nodes:
                logger.warning("Graph has no nodes")
                return []
                
            # 获取节点嵌入
            embeddings = []
            valid_nodes = []
            for node in nodes:
                if node in self.node_embeddings:
                    embeddings.append(self.node_embeddings[node])
                    valid_nodes.append(node)
                    
            if not embeddings:
                logger.warning("No valid embeddings found")
                return self._fallback_potential_edges(G)
                
            # 计算相似度
            embeddings = np.array(embeddings, dtype=np.float32)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10
            normalized_embeddings = embeddings / norms
            
            # 使用批处理计算相似度
            batch_size = min(1000, len(valid_nodes))
            potential_edges = []
            total_batches = (len(valid_nodes) + batch_size - 1) // batch_size
            
            for i in range(0, len(valid_nodes), batch_size):
                end_i = min(i + batch_size, len(valid_nodes))
                batch_similarities = np.dot(
                    normalized_embeddings[i:end_i],
                    normalized_embeddings.T
                )
                
                # 找出高相似度的边
                for batch_idx, similarities in enumerate(batch_similarities):
                    global_idx = i + batch_idx
                    source = valid_nodes[global_idx]
                    
                    # 使用numpy操作找出高相似度的目标节点
                    high_sim_indices = np.where(similarities > threshold)[0]
                    for target_idx in high_sim_indices:
                        if global_idx != target_idx:
                            target = valid_nodes[target_idx]
                            if not G.has_edge(source, target):
                                risk_score = (
                                    self.node_risks.get(source, 0) +
                                    self.node_risks.get(target, 0)
                                ) / 2
                                if risk_score >= Config.SUSPICIOUS_THRESHOLD:
                                    potential_edges.append({
                                        'source': source,
                                        'target': target,
                                        'similarity': float(similarities[target_idx]),
                                        'risk_score': float(risk_score)
                                    })
                
                progress = ((i + batch_size) / len(valid_nodes)) * 100
                logger.info(f"Similarity computation: {progress:.1f}% complete")
                
            # 按风险分数排序并限制数量
            potential_edges.sort(key=lambda x: (-x['risk_score'], -x['similarity']))
            potential_edges = potential_edges[:100]
            
            compute_time = time.time() - start_time
            logger.info(f"Found {len(potential_edges)} potential suspicious edges in {compute_time:.2f} seconds")
            self.potential_edges = potential_edges
            return potential_edges
            
        except Exception as e:
            logger.error(f"Error predicting potential edges: {e}")
            logger.error(traceback.format_exc())
            return self._fallback_potential_edges(G)
    def _fallback_potential_edges(self, G):
        logger.warning("Using fallback method for potential edge prediction")
        potential_edges = []
        for node in G.nodes():
            neighbors = set(G.successors(node)).union(set(G.predecessors(node)))
            for neighbor in neighbors:
                second_degree = set(G.successors(neighbor)).union(set(G.predecessors(neighbor)))
                second_degree = second_degree - neighbors - {node}
                for target in second_degree:
                    if not G.has_edge(node, target):
                        common_neighbors = len(set(G.neighbors(node)).intersection(set(G.neighbors(target))))
                        similarity = float(common_neighbors / max(len(set(G.neighbors(node))), len(set(G.neighbors(target)))))
                        source_risk = float(self.node_risks.get(node, 0.5))
                        target_risk = float(self.node_risks.get(target, 0.5))
                        risk_score = float((source_risk + target_risk) / 2)
                        potential_edges.append({
                            'source': node,
                            'target': target,
                            'similarity': similarity,
                            'risk_score': risk_score
                        })

        potential_edges.sort(key=lambda x: (x['risk_score'], x['similarity']), reverse=True)
        result = potential_edges[:50]
        self.potential_edges = result
        logger.info(f"Generated {len(result)} potential edges using fallback method")
        return result
    def cluster_similar_nodes(self, min_samples=3, eps=0.4):
        if not self.node_embeddings:
            logger.error("Node embeddings not computed")
            return self._fallback_clustering(min_samples)
        
        try:
            start_time = time.time()

            nodes = list(self.node_embeddings.keys())
            if len(nodes) < min_samples:
                logger.warning(f"Not enough nodes ({len(nodes)}) for clustering, minimum {min_samples} required")
                return self._fallback_clustering(min_samples)
            logger.info(f"Clustering {len(nodes)} nodes with min_samples={min_samples}, eps={eps}")
            try:
                if self.device.type == 'cuda' and hasattr(torch, 'cuda'):
                    logger.info("Attempting to use GPU-accelerated clustering")
                    # 预先将所有嵌入转换为numpy数组
                    embeddings = np.array([self.node_embeddings[node] for node in nodes], dtype=np.float32)
                    embeddings_tensor = torch.from_numpy(embeddings).to(self.device)
                    batch_size = min(1024, len(nodes))
                    distance_matrix = torch.zeros((len(nodes), len(nodes)), device=self.device)
                    with torch.amp.autocast(device_type='cuda'):
                        for i in range(0, len(nodes), batch_size):
                            end_idx = min(i + batch_size, len(nodes))
                            batch_embeddings = embeddings_tensor[i:end_idx]
                            for j in range(0, len(nodes), batch_size):
                                end_j = min(j + batch_size, len(nodes))
                                other_embeddings = embeddings_tensor[j:end_j]
                                batch_distances = torch.cdist(batch_embeddings, other_embeddings, p=2.0)
                                distance_matrix[i:end_idx, j:end_j] = batch_distances
                                progress = ((i * len(nodes) + (j + batch_size)) / (len(nodes) * len(nodes))) * 100
                                if (i // batch_size * (len(nodes) // batch_size) + j // batch_size) % 10 == 0:
                                    logger.info(f"Distance computation: {progress:.1f}% complete")
                    distance_matrix_np = distance_matrix.cpu().numpy()
                    torch.cuda.empty_cache()
                    from sklearn.cluster import DBSCAN
                    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='precomputed')
                    clusters = dbscan.fit_predict(distance_matrix_np)
                    
                    logger.info("Successfully completed GPU-accelerated clustering")
                else:
                    logger.info("Using standard CPU-based clustering")
                    embeddings_np = np.array([self.node_embeddings[node] for node in nodes])
                    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
                    clusters = dbscan.fit_predict(embeddings_np)
            except Exception as e:
                logger.error(f"Error in GPU-accelerated clustering: {e}, falling back to CPU-based clustering")
                embeddings_np = np.array([self.node_embeddings[node] for node in nodes])
                dbscan = DBSCAN(eps=eps, min_samples=min_samples)
                clusters = dbscan.fit_predict(embeddings_np)
            cluster_results = {}
            for i, cluster_id in enumerate(clusters):
                if cluster_id == -1:
                    continue
                cluster_id = int(cluster_id)
                if cluster_id not in cluster_results:
                    cluster_results[cluster_id] = []
                
                cluster_results[cluster_id].append({
                    'node': nodes[i],
                    'risk_score': float(self.node_risks.get(nodes[i], 0))  # 确保使用Python的float类型
                })
            enriched_clusters = {}
            for cluster_id, members in cluster_results.items():
                avg_risk = np.mean([m['risk_score'] for m in members])
                sorted_members = sorted(members, key=lambda x: x['risk_score'], reverse=True)
                
                enriched_clusters[cluster_id] = {
                    'members': sorted_members,
                    'count': len(members),
                    'avg_risk_score': float(avg_risk),  # 确保使用Python的float类型
                    'risk_level': 'high' if avg_risk > 0.7 else 'medium' if avg_risk > 0.4 else 'low'
                }
            if not enriched_clusters:
                logger.warning("No clusters found with DBSCAN, using fallback method")
                return self._fallback_clustering(min_samples)
                
            compute_time = time.time() - start_time
            logger.info(f"Found {len(enriched_clusters)} clusters based on embeddings in {compute_time:.2f} seconds")
            self.gnn_clusters = enriched_clusters
            return enriched_clusters
            
        except Exception as e:
            logger.error(f"Error clustering nodes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_clustering(min_samples)
            
    def _fallback_clustering(self, min_group_size=3):
        logger.warning("Using fallback clustering method based on graph structure")
        high_risk_nodes = [node for node, risk in self.node_risks.items() if risk > 0.6]

        clusters = {}
        cluster_id = 0

        for i, node in enumerate(high_risk_nodes):
            if i > 20:
                break
            related_nodes = []
            for other_node, risk in self.node_risks.items():
                if node != other_node and risk > 0.4:
                    if np.random.random() < 0.3:
                        related_nodes.append({
                            'node': other_node,
                            'risk_score': float(risk)
                        })

            if len(related_nodes) >= min_group_size - 1:
                all_members = [{'node': node, 'risk_score': float(self.node_risks.get(node, 0.5))}] + related_nodes
                avg_risk = float(np.mean([m['risk_score'] for m in all_members]))
                
                clusters[cluster_id] = {
                    'members': sorted(all_members, key=lambda x: x['risk_score'], reverse=True),
                    'count': len(all_members),
                    'avg_risk_score': float(avg_risk),
                    'risk_level': 'high' if avg_risk > 0.7 else 'medium' if avg_risk > 0.4 else 'low'
                }
                cluster_id += 1
        
        logger.info(f"Created {len(clusters)} clusters using fallback method")
        self.gnn_clusters = clusters
        return clusters
    
    def enhance_graph(self, G):
        if not self.node_risks:
            logger.warning("Node risks not predicted, cannot enhance graph")
            self._generate_random_risk_scores(G)
            
        try:
            for node in G.nodes():
                if node in self.node_risks:
                    G.nodes[node]['gnn_risk_score'] = self.node_risks[node]
                else:
                    risk = 0.2 + np.random.random() * 0.3
                    G.nodes[node]['gnn_risk_score'] = risk
                    self.node_risks[node] = risk

            potential_edges_added = 0
            for edge in self.potential_edges:
                source = edge['source']
                target = edge['target']
                if source in G.nodes() and target in G.nodes():
                    try:
                        G.add_edge(source, target, 
                                 is_potential=True,
                                 similarity=edge['similarity'], 
                                 risk_score=edge['risk_score'],
                                 weight=0.0)
                        potential_edges_added += 1
                    except Exception as e:
                        logger.warning(f"Failed to add potential edge {source}->{target}: {e}")
                        continue
            logger.info(f"Enhanced graph with {potential_edges_added} potential edges")
            return G
        except Exception as e:
            logger.error(f"Error enhancing graph: {e}")
            return G
            
    def _generate_random_risk_scores(self, G):
        for node in G.nodes():
            if node not in self.node_risks:
                degree = G.degree(node)
                base_risk = min(0.2 + 0.05 * math.log(degree + 1), 0.7)
                risk = base_risk + np.random.normal(0, 0.1)
                risk = max(0.1, min(0.9, risk))
                self.node_risks[node] = risk 