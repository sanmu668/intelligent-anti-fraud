import os

class Config:
    # Application settings
    DEBUG = True
    TESTING = False
    
    # Model files
    GBC_MODEL_PATH = "E:/DevelopmentProject/BigDataCompetition/IntelligentAntiFraud/API-cope/model/gbc_model.pkl"
    RF_MODEL_PATH = "E:/DevelopmentProject/BigDataCompetition/IntelligentAntiFraud/API-cope/model/rf_model.pkl"
    GNN_MODEL_PATH = "E:/DevelopmentProject/BigDataCompetition/IntelligentAntiFraud/API-cope/model/fraud_gnn_model.pth"
    MLP_MODEL_PATH = "E:/DevelopmentProject/BigDataCompetition/IntelligentAntiFraud/API-cope/model/best_mlp_model.pth"
    
    # Data file
    DATA_PATH = "E:/DevelopmentProject/BigDataCompetition/IntelligentAntiFraud/API-cope/data/balanced_data.csv"
    
    # Cache settings
    CACHE_TIMEOUT = 5  # seconds
    
    # API settings
    MAX_TRANSACTIONS = 10000
    DEFAULT_PAGE_SIZE = 20
    
    # Risk thresholds
    HIGH_RISK_THRESHOLD = 0.7
    VERY_HIGH_RISK_THRESHOLD = 0.8
    SUSPICIOUS_THRESHOLD = 0.5
    
    # Graph settings
    MAX_EDGES = 3000
    NODE_AGGREGATION_THRESHOLD = 5
    
    # WebSocket settings
    WS_NAMESPACE = '/ws/monitor'
    
    @classmethod
    def init_app(cls):
        """初始化应用配置"""
        # 验证路径
        cls.validate_paths()
        
        # 打印当前配置信息
        print(f"Current configuration:")
        print(f"Model files:")
        print(f"  GBC: {cls.GBC_MODEL_PATH}")
        print(f"  RF: {cls.RF_MODEL_PATH}")
        print(f"  GNN: {cls.GNN_MODEL_PATH}")
        print(f"  MLP: {cls.MLP_MODEL_PATH}")
        print(f"\nData file:")
        print(f"  Data: {cls.DATA_PATH}")
    
    @classmethod
    def validate_paths(cls):
        """验证所有配置的文件路径是否存在"""
        paths_to_check = {
            'GBC_MODEL_PATH': cls.GBC_MODEL_PATH,
            'RF_MODEL_PATH': cls.RF_MODEL_PATH,
            'GNN_MODEL_PATH': cls.GNN_MODEL_PATH,
            'MLP_MODEL_PATH': cls.MLP_MODEL_PATH,
            'DATA_PATH': cls.DATA_PATH
        }
        
        missing_files = []
        for name, path in paths_to_check.items():
            if not os.path.exists(path):
                missing_files.append(f"{name}: {path}")
        
        if missing_files:
            print("Warning: Missing required files:")
            for missing in missing_files:
                print(f"  - {missing}")
            print("\nPlease ensure all required files are in the correct locations.") 