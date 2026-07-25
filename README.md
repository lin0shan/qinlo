# 个人商业助手

美妆行业进销存 + 会员管理一体化工具。

**移动优先 · 本地部署 · PWA 离线 · 系统托盘 · 零月费**

## 快速开始

### Docker 部署

```bash
cd business-helper
cp .env.example .env
docker compose up -d
```

浏览器访问 `http://localhost`。

### 本地开发

**后端**

```bash
cd backend
pip install -r requirements.txt
python run.py
```

API 文档：`http://localhost:8000/docs`

**前端**

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`

### 构建 Windows 安装包

```bash
# 1. 创建打包专用虚拟环境并安装依赖
python -m venv build_venv
build_venv\Scripts\python -m pip install -r backend\requirements.txt pyinstaller

# 2. 运行构建脚本
python build_installer.py
```

安装包生成在 `build\个人商业助手_v1.0.0_setup.exe`。

运行安装包：
- 双击 `个人商业助手_v1.0.0_setup.exe` 完成安装
- 双击桌面快捷方式启动
- 系统托盘出现蓝色 BH 图标，浏览器自动打开
- 托盘右键菜单：打开 / 退出

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python FastAPI + SQLAlchemy + SQLite (WAL) |
| 前端 | Vue 3 + TypeScript + Vant 4 + Vite |
| 打包 | PyInstaller + NSIS |
| 离线 | PWA + Service Worker + IndexedDB |
| 部署 | Docker + Nginx |

## 功能清单

- 商品管理（CRUD、搜索、条码、图片压缩）
- 采购入库 / 销售出库 / 退货
- 库存看板（实时计算、低库存预警）
- 盘点（差异对比、修正）
- 会员管理（档案、积分、消费记录）
- 发货管理（快递录入、状态追踪）
- 销售报表（日报/月报、热销排行）
- 数据备份恢复（手动 + 自动定时）
- PWA 离线（离线浏览、离线开单、联网自动同步）
- Excel 批量导入商品
- 系统托盘运行，无控制台窗口

## 项目结构

```
business-helper/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config.py         # 配置
│   │   ├── database.py       # 数据库 + WAL checkpoint
│   │   ├── models/           # 数据模型
│   │   ├── routers/          # 路由模块
│   │   ├── schemas/          # Pydantic 校验
│   │   ├── services/         # 业务逻辑
│   │   ├── middleware/       # 认证 + 日志
│   │   └── utils/            # 条码 + 图片
│   ├── alembic/              # 数据库迁移
│   ├── scripts/              # 工具脚本
│   └── tests/                # pytest
├── frontend/
│   └── src/
│       ├── views/            # 页面组件
│       ├── components/       # 通用组件
│       ├── db/               # IndexedDB 离线层
│       ├── composables/      # 组合式函数
│       └── router/           # 路由
├── nginx/conf.d/             # Nginx 配置
├── docs/                     # 文档
├── build_installer.py        # 构建脚本
├── installer.nsi             # NSIS 安装脚本
└── docker-compose.yml
```

## 运行测试

```bash
cd backend
pytest -v
```

## 文档

- [产品说明书](产品说明书V1.md)
- [扫码入库出库现状梳理](docs/扫码入库出库现状梳理.md)
