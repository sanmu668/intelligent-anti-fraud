# 智能反欺诈系统

一个使用图分析、机器学习和实时可视化技术的高级交易反欺诈检测系统。

## 项目概述

本项目实现了一个智能反欺诈系统，结合图分析、机器学习和交互式可视化技术来检测和分析潜在的欺诈交易。系统使用图神经网络（GNN）进行高级模式识别，并提供交易网络的实时可视化分析。

## 项目结构

```
IntelligentAntiFraud/
├── API-cope/                  # 后端API服务器
│   ├── app/                   # 主应用程序代码
│   │   ├── routes/           # API路由定义
│   │   ├── models/           # 机器学习模型和GNN实现
│   │   └── utils/            # 工具函数
│   ├── data/                 # 数据存储
│   ├── model/                # 训练好的模型文件
│   ├── requirements.txt      # Python依赖项
│   └── main.py              # 应用程序入口点
│
├── vue-app/                   # 前端应用
│   ├── src/                  # 源代码
│   ├── public/               # 静态资源
│   ├── package.json          # Node.js依赖项
│   └── vite.config.ts        # Vite配置
│
├── Visual/                    # 可视化组件
│
└── backend-AI/               # AI对话
```

## 技术栈

### 后端 (API-cope)
- **框架**: Flask (Python)
- **图处理**: NetworkX
- **机器学习**: 
  - 图神经网络 (GNN)
  - PyTorch Geometric
  - Pandas 数据处理
- **API**: RESTful API，JSON响应格式
- **日志**: 自定义日志系统，用于调试和监控

### 前端 (vue-app)
- **框架**: Vue.js 3 + TypeScript
- **构建工具**: Vite
- **包管理器**: npm/yarn
- **可视化**: 
  - ECharts 图表可视化
  - 自定义 D3.js 组件
- **状态管理**: Vuex/Pinia
- **UI组件**: 自定义现代化设计组件

## 核心功能

1. **基于图的交易分析**
   - 实时交易网络可视化
   - 账户间路径分析
   - 风险评分计算
   - 社群检测

2. **高级欺诈检测**
   - 基于GNN的模式识别
   - 实时风险评估
   - 异常检测
   - 相似交易聚类分析

3. **交互式可视化**
   - 动态图形渲染
   - 风险等级突出显示
   - 交易路径追踪
   - 聚类可视化

## 安装说明

### 后端设置
1. 进入API-cope目录：
   ```bash
   cd API-cope
   ```

2. 安装Python依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 启动Flask服务器：
   ```bash
   python main.py
   ```

### 前端设置
1. 进入vue-app目录：
   ```bash
   cd vue-app
   ```

2. 安装Node.js依赖：
   ```bash
   npm install
   ```

3. 启动开发服务器：
   ```bash
   npm run dev
   ```

## API文档

### 主要接口

#### 图分析
- `POST /api/graph/analysis/path`
  - 分析交易路径并返回网络结构
  - 支持时间范围过滤和GNN增强分析
  - 返回节点、边和风险分析数据

## 参与贡献

1. Fork 本仓库
2. 创建您的特性分支
3. 提交您的更改
4. 推送到分支
5. 创建新的Pull Request

## 开源协议

本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情 