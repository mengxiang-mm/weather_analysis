# 🌤 中国天气预报分析系统

基于 **墨迹天气** 的全国天气预报爬虫 + 数据分析 + 可视化 + 前端导航页面。

---

## 📂 项目结构

```
weather_analysis/
├── weather_analysis.py              # 入口文件（python weather_analysis.py）
├── weather_analysis_pkg/            # 核心模块包
│   ├── __init__.py
│   ├── config.py                    # 配置管理（加载 province_data.json）
│   ├── scraper.py                   # 爬虫模块（cloudscraper + UA 轮换）
│   ├── cleaner.py                   # 数据清洗与存储
│   ├── analyzer.py                  # 统计分析
│   ├── visualizer.py                # 可视化（4 类图表）
│   └── cli.py                       # 命令行入口与流程编排
├── province_data.json               # 共享数据（前后端统一拼音映射）
├── china_weather.html               # 中国天气导航前端页面（骨架屏加载）
├── beijing_page.html                # 北京地区景区天气页面（参考/备用）
├── requirements.txt                 # Python 依赖清单
├── .gitignore                       # Git 忽略规则
├── README.md                        # 本文件
└── weather_output/                  # 脚本运行输出
    ├── weather_data.csv             # 原始爬取数据
    ├── weather_data_clean.csv       # 清洗后数据
    ├── province_temp_summary.csv    # 各省温度统计
    ├── 01_avg_temp_comparison.png   # 平均温度对比图
    ├── 02_temp_heatmap.png          # 温度热力图
    ├── 03_temp_trends.png           # 温度趋势图
    └── 04_weather_pie_chart.png     # 天气状况饼图
```

---

## 🚀 在其他电脑本地部署

### 前提条件

- **Python** 3.10 或更高版本
- **Git**（用于克隆仓库）
- 网络连接（首次运行需要下载依赖）

### 部署步骤

#### 1️⃣ 克隆仓库

```bash
git clone <你的仓库地址>
cd weather_analysis
```

#### 2️⃣ 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

#### 4️⃣ 运行爬虫与数据分析

```bash
python weather_analysis.py
```

脚本会自动：
1. 爬取全国 34 个省级行政区的 7 日天气预报
2. 清洗数据并保存为 CSV
3. 生成 4 张统计图表到 `weather_output/` 目录

#### 5️⃣ 打开前端导航页面

直接用浏览器打开 `china_weather.html`（双击即可）

---

## 🧩 项目架构（v2.0）

```
weather_analysis.py          ← 入口，保持向后兼容
weather_analysis_pkg/        ← 模块化拆分
├── config.py                ← 配置 + province_data.json 加载
├── scraper.py               ← 爬虫 + UA 轮换 + 样本数据
├── cleaner.py               ← 数据清洗 + CSV 存储
├── analyzer.py              ← 分组统计 + 分布分析
├── visualizer.py            ← 4 类图表生成
└── cli.py                   ← 主流程编排 + 命令行
province_data.json           ← 前后端共享数据（拼音/坐标）
```

---

## 🔧 自定义配置

编辑 `weather_analysis_pkg/config.py` 中的配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DELAY_RANGE` | 爬虫请求间隔（秒） | `(1.5, 3.5)` |
| `TIMEOUT` | 请求超时（秒） | `20` |
| `MAX_RETRIES` | 失败重试次数 | `3` |
| `OUTPUT_DIR` | 输出目录 | `./weather_output` |
| `USER_AGENTS` | UA 池（随机轮换） | 7 个浏览器 UA |

前端拼音映射统一由 `province_data.json` 管理，不再硬编码。

> ⚠️ **注意**：请合理设置爬虫延迟，避免对目标服务器造成压力。

---

## 🌐 前端页面说明

`china_weather.html` 是一个独立的静态页面：

- **中国地图**：基于 ECharts + 阿里云 DataV 地理数据
- **省份列表**：按地区分组，支持搜索
- **点击跳转**：直接打开墨迹天气对应城市预报页面
- **温度色标**：地图颜色直观反映各省日均最高温

无需任何后端服务，双击即可使用。

---

## ⚙️ 依赖说明

| 包名 | 用途 |
|------|------|
| `cloudscraper` | 绕过 Cloudflare 反爬限制 |
| `beautifulsoup4` | HTML 解析 |
| `lxml` | 底层 XML/HTML 解析器 |
| `pandas` | 数据清洗与统计分析 |
| `numpy` | 数值计算 |
| `matplotlib` | 基础绘图 |
| `seaborn` | 统计图表美化 |

---

## 📝 License

本项目仅供学习和个人使用。数据来源为[墨迹天气](https://tianqi.moji.com)，请遵守相关服务条款。
