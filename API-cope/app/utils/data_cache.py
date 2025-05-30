import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import networkx as nx
from networkx.algorithms import community
from app.utils.logger import logger
from app.models.gnn_utils import GNNModel
from app.config.config import Config
import os
import joblib

class DataCache:
    _instance = None
    _data = None
    _last_update = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DataCache()
        return cls._instance
    
    def get_data(self, force_reload=False):
        """获取数据，如果需要则重新加载"""
        if self._data is None or force_reload:
            try:
                self._data = pd.read_csv(Config.DATA_PATH)
                print(f"Successfully loaded data from {Config.DATA_PATH}")
            except Exception as e:
                print(f"Error loading data: {e}")
                self._data = pd.DataFrame()  # 返回空DataFrame而不是None
        return self._data

    def get_transaction_by_id(self, transaction_id):
        """根据交易ID获取单条交易记录"""
        data = self.get_data()
        if transaction_id in data.index:
            return data.loc[transaction_id].to_dict()
        return None
        
    def get_transactions_by_user(self, user_id, limit=100):
        """获取用户的交易记录"""
        data = self.get_data()
        user_transactions = data[
            (data['nameOrig'] == user_id) | 
            (data['nameDest'] == user_id)
        ].head(limit)
        return user_transactions.to_dict('records')
        
    def get_high_risk_transactions(self, risk_threshold=0.7, limit=100):
        """获取高风险交易"""
        data = self.get_data()
        high_risk = data[data['risk_score'] >= risk_threshold].head(limit)
        return high_risk.to_dict('records')
        
    def get_transaction_stats(self):
        """获取交易统计信息"""
        data = self.get_data()
        stats = {
            'total_transactions': len(data),
            'total_amount': float(data['amount'].sum()),
            'avg_amount': float(data['amount'].mean()),
            'max_amount': float(data['amount'].max()),
            'min_amount': float(data['amount'].min()),
            'fraud_count': int(data['isFraud'].sum()),
            'fraud_rate': float(data['isFraud'].mean())
        }
        return stats

    def __init__(self):
        self.transactions = []
        self.alerts = []
        self.last_update = None
        self.df = None
        self.graph = None
        self.communities = None
        self.group_cache = {}
        self.cache_timeout = Config.CACHE_TIMEOUT
        self._load_models()

    def _load_models(self):
        try:
            self.models = {
                'gbc': joblib.load(Config.GBC_MODEL_PATH),
                'rf': joblib.load(Config.RF_MODEL_PATH)
            }
            self.current_model = 'gbc'
            logger.info(f"Successfully loaded models: {list(self.models.keys())}")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.models = {}
            self.current_model = None

        try:
            self.gnn_model = GNNModel(model_path=Config.GNN_MODEL_PATH)
            logger.info("GNN model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load GNN model: {e}")
            self.gnn_model = None

    def should_refresh(self):
        """检查是否需要刷新数据"""
        if not self.last_update:
            return True
        return (datetime.now() - self.last_update).total_seconds() > self.cache_timeout

    def load_data(self):
        """Load and process transaction data"""
        try:
            if not self.should_refresh():
                logger.info("Using cached data")
                return True

            logger.info("Loading transaction data...")
            
            if not os.path.exists(Config.DATA_PATH):
                logger.error(f"Data file not found: {Config.DATA_PATH}")
                return False

            # 1. 首先只读取必要的列，减少内存使用
            columns = ['step', 'type', 'amount', 'nameOrig', 'oldbalanceOrg', 'newbalanceOrig', 
                      'nameDest', 'oldbalanceDest', 'newbalanceDest', 'isFraud']
            
            # 2. 使用dtype指定数据类型，优化内存使用
            dtype_dict = {
                'step': 'int32',
                'type': 'category',
                'amount': 'float32',
                'nameOrig': 'category',
                'nameDest': 'category',
                'oldbalanceOrg': 'float32',
                'newbalanceOrig': 'float32',
                'oldbalanceDest': 'float32',
                'newbalanceDest': 'float32',
                'isFraud': 'int8'
            }
            
            # 3. 使用nrows限制最大行数
            max_rows = Config.MAX_TRANSACTIONS * 2  # 预留一些空间用于后续处理
            
            # 4. 一次性读取数据，避免多次IO
            self.df = pd.read_csv(
                Config.DATA_PATH,
                usecols=columns,
                dtype=dtype_dict,
                nrows=max_rows
            )
            
            # 5. 添加时间戳列（基于step列）
            current_time = datetime.now()
            start_date = current_time - timedelta(days=30)
            self.df['timestamp'] = start_date + pd.to_timedelta(self.df['step'], unit='h')  # 使用小写'h'
            
            # 6. 计算风险分数
            self.df['risk_score'] = self._calculate_risk_scores(self.df)
            
            # 7. 添加风险类型
            self.df['risk_type'] = self.df.apply(self.determine_risk_type, axis=1)
            
            # 8. 转换为记录格式
            self.transactions = self.df.to_dict('records')
            self.last_update = datetime.now()

            # 9. 生成预警
            self.generate_alerts()

            # 10. 构建交易网络
            self._build_graph()

            logger.info(f"Successfully loaded {len(self.df)} transactions")
            return True

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _calculate_risk_scores(self, df):
        """Calculate risk scores based on multiple risk factors"""
        try:
            # 1. 基于金额的风险评分 - 使用向量化操作
            amount_risk = np.zeros(len(df))
            amount_thresholds = [(1000000, 0.3), (500000, 0.2), (100000, 0.1)]
            for threshold, score in amount_thresholds:
                amount_risk += (df['amount'] > threshold).astype(float) * score
            
            logger.info(f"Amount risk stats: mean={amount_risk.mean():.3f}, max={amount_risk.max():.3f}, "
                       f"num_high_risk={np.sum(amount_risk > 0.3)}")
            
            # 2. 基于余额变化的风险评分
            balance_change_risk = np.zeros(len(df))
            
            # 检查余额变化异常
            orig_balance_diff = df['newbalanceOrig'] - df['oldbalanceOrg']
            dest_balance_diff = df['newbalanceDest'] - df['oldbalanceDest']
            
            # 余额变化不符合交易金额（考虑手续费等因素，允许1%的误差）
            balance_mismatch = (abs(orig_balance_diff + df['amount']) > df['amount'] * 0.01) | \
                             (abs(dest_balance_diff - df['amount']) > df['amount'] * 0.01)
            balance_change_risk += balance_mismatch.astype(float) * 0.2
            
            # 账户清空（余额降至接近于0）
            account_cleared = (df['newbalanceOrig'] < df['amount'] * 0.01) & (df['oldbalanceOrg'] > 10000)
            balance_change_risk += account_cleared.astype(float) * 0.3
            
            logger.info(f"Balance change risk stats: mean={balance_change_risk.mean():.3f}, "
                       f"max={balance_change_risk.max():.3f}, "
                       f"num_high_risk={np.sum(balance_change_risk > 0.3)}")
            
            # 3. 基于交易频率的风险评分 - 使用时间窗口聚合
            df = df.sort_values('timestamp')
            time_window = '24h'
            
            # 计算每个账户在24小时窗口内的交易次数和金额
            freq_orig = df.groupby('nameOrig').rolling(
                window=time_window,
                on='timestamp',
                min_periods=1,
                closed='left'
            ).agg({
                'amount': ['count', 'sum']
            }).reset_index()
            
            freq_orig.columns = ['nameOrig', 'timestamp', 'tx_count', 'tx_amount']
            
            freq_dest = df.groupby('nameDest').rolling(
                window=time_window,
                on='timestamp',
                min_periods=1,
                closed='left'
            ).agg({
                'amount': ['count', 'sum']
            }).reset_index()
            
            freq_dest.columns = ['nameDest', 'timestamp', 'tx_count', 'tx_amount']
            
            # 合并发送方和接收方的统计
            df = df.merge(freq_orig[['nameOrig', 'timestamp', 'tx_count', 'tx_amount']], 
                         on=['nameOrig', 'timestamp'], 
                         how='left')
            df = df.merge(freq_dest[['nameDest', 'timestamp', 'tx_count', 'tx_amount']], 
                         on=['nameDest', 'timestamp'], 
                         how='left',
                         suffixes=('_orig', '_dest'))
            
            # 计算频率风险
            freq_risk = np.zeros(len(df))
            
            # 基于交易次数的风险
            total_tx_count = df['tx_count_orig'].fillna(0) + df['tx_count_dest'].fillna(0)
            freq_risk += (total_tx_count > 20).astype(float) * 0.3
            freq_risk += ((total_tx_count > 10) & (total_tx_count <= 20)).astype(float) * 0.2
            freq_risk += ((total_tx_count > 5) & (total_tx_count <= 10)).astype(float) * 0.1
            
            # 基于24小时交易总额的风险
            total_tx_amount = df['tx_amount_orig'].fillna(0) + df['tx_amount_dest'].fillna(0)
            freq_risk += (total_tx_amount > 1000000).astype(float) * 0.2
            freq_risk += ((total_tx_amount > 500000) & (total_tx_amount <= 1000000)).astype(float) * 0.1
            
            logger.info(f"Frequency risk stats: mean={freq_risk.mean():.3f}, "
                       f"max={freq_risk.max():.3f}, "
                       f"num_high_risk={np.sum(freq_risk > 0.3)}")
            
            # 4. 基于交易模式的风险评分
            pattern_risk = np.zeros(len(df))
            
            # 检查环形交易
            cycle_df = df.merge(
                df,
                left_on=['nameOrig', 'timestamp'],
                right_on=['nameDest', 'timestamp'],
                suffixes=('', '_reverse')
            )
            cycle_df = cycle_df[
                (cycle_df['nameDest'] == cycle_df['nameOrig_reverse']) & 
                (abs(cycle_df['amount'] - cycle_df['amount_reverse']) < cycle_df['amount'] * 0.01)  # 金额相近
            ]
            if not cycle_df.empty:
                pattern_risk[cycle_df.index] = 0.3
            
            # 检查快进快出
            quick_out = df[df['type'].isin(['CASH_OUT', 'TRANSFER'])].copy()
            quick_out['next_hour'] = quick_out['timestamp'] + pd.Timedelta(hours=1)
            
            quick_matches = quick_out.merge(
                df,
                left_on=['nameDest'],
                right_on=['nameOrig'],
                suffixes=('', '_next')
            )
            quick_matches = quick_matches[
                (quick_matches['timestamp_next'] >= quick_matches['timestamp']) &
                (quick_matches['timestamp_next'] <= quick_matches['next_hour']) &
                (quick_matches['amount_next'] >= quick_matches['amount'] * 0.9)  # 金额相近
            ]
            if not quick_matches.empty:
                pattern_risk[quick_matches.index] = np.maximum(
                    pattern_risk[quick_matches.index],
                    0.25
                )
            
            logger.info(f"Pattern risk stats: mean={pattern_risk.mean():.3f}, "
                       f"max={pattern_risk.max():.3f}, "
                       f"num_high_risk={np.sum(pattern_risk > 0.3)}")
            
            # 5. 合并所有风险因素
            risk_scores = amount_risk + freq_risk + pattern_risk + balance_change_risk
            
            # 6. 考虑已知欺诈标记
            risk_scores = np.maximum(risk_scores, df['isFraud'].astype(float))
            
            # 确保风险分数在0-1之间
            risk_scores = risk_scores.clip(0, 1)
            
            # 7. 对特定高风险场景进行提升
            high_risk_conditions = [
                ((df['amount'] > 1000000) & (df['type'] == 'CASH_OUT'), 0.8),
                ((freq_risk > 0.2) & (df['amount'] > 500000), 0.75),
                ((pattern_risk > 0.2) & (df['amount'] > 300000), 0.85),
                (account_cleared & (df['amount'] > 100000), 0.9)
            ]
            
            for condition, score in high_risk_conditions:
                risk_scores = np.maximum(risk_scores, condition.astype(float) * score)
            
            # 8. 添加随机扰动避免风险分数过于集中
            noise = np.random.normal(0, 0.05, len(risk_scores))  # 5%的随机扰动
            risk_scores = (risk_scores + noise).clip(0, 1)
            
            logger.info(f"Final risk score stats: mean={risk_scores.mean():.3f}, "
                       f"max={risk_scores.max():.3f}, "
                       f"num_high_risk={np.sum(risk_scores > 0.7)}")
            
            # 9. 风险分数分布统计
            risk_ranges = [(0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.0)]
            for low, high in risk_ranges:
                count = np.sum((risk_scores > low) & (risk_scores <= high))
                logger.info(f"Risk score range {low:.1f}-{high:.1f}: {count} transactions "
                          f"({count/len(risk_scores)*100:.1f}%)")
            
            return risk_scores
            
        except Exception as e:
            logger.error(f"Error calculating risk scores: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return np.zeros(len(df))

    def determine_risk_type(self, row):
        """Determine risk type based on transaction characteristics"""
        try:
            if row['risk_score'] > 0.8:
                if row['amount'] > 500000:
                    return '大额交易'
                return '身份盗用'
            elif row['risk_score'] > 0.7:
                return '洗钱行为'
            elif row['risk_score'] > 0.5:
                return '可疑行为'
            return '正常交易'
        except Exception as e:
            logger.error(f"Error determining risk type: {e}")
            return '未知风险'

    def generate_alerts(self):
        """Generate alerts based on high-risk transactions"""
        try:
            self.alerts = []
            high_risk_txs = self.df[self.df['risk_score'] > 0.7]
            
            for _, tx in high_risk_txs.iterrows():
                alert = {
                    'id': len(self.alerts) + 1,
                    'timestamp': tx['timestamp'].isoformat(),
                    'type': tx['risk_type'],
                    'risk_level': '高风险' if tx['risk_score'] > 0.8 else '中风险',
                    'description': f"账户 {tx['nameOrig']} 向 {tx['nameDest']} 发起 {tx['type']} 交易，金额 ¥{tx['amount']:,.2f}",
                    'status': 'pending'
                }
                self.alerts.append(alert)
            
            logger.info(f"Generated {len(self.alerts)} alerts")
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")

    def _build_graph(self):
        """Build transaction network graph"""
        try:
            G = nx.DiGraph()
            
            # Add edges with weights based on transaction amounts
            for _, row in self.df.iterrows():
                G.add_edge(
                    row['nameOrig'],
                    row['nameDest'],
                    weight=float(row['amount']),
                    risk_score=float(row['risk_score'])
                )
            
            self.graph = G
            
            # Find communities using Louvain method
            self.communities = list(community.louvain_communities(G.to_undirected()))
            logger.info(f"Built graph with {len(G.nodes)} nodes and {len(G.edges)} edges")
            
        except Exception as e:
            logger.error(f"Error building graph: {e}")
            self.graph = None
            self.communities = None

    def _preprocess_chunk(self, chunk):
        # 保持原有的_preprocess_chunk方法代码不变
        # ... (从原文件复制_preprocess_chunk方法的内容)
        pass

    def _precalculate_risk_subgraphs(self):
        # 保持原有的_precalculate_risk_subgraphs方法代码不变
        # ... (从原文件复制_precalculate_risk_subgraphs方法的内容)
        pass

    def prepare_batch_features(self, df):
        # 保持原有的prepare_batch_features方法代码不变
        # ... (从原文件复制prepare_batch_features方法的内容)
        pass 