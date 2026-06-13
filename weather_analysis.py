#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
================================================================================
    天气数据分析系统  —  墨迹天气爬虫 + 数据清洗 + 统计分析 + 可视化
================================================================================

功能流程：
  1. 爬虫模块  →  requests + BeautifulSoup 抓取墨迹天气未来 7 日预报
  2. 存储模块  →  按省份/城市结构化写入 CSV（UTF-8 with BOM）
  3. 分析模块  →  pandas 分组统计：均值、分布、极值
  4. 可视化    →  matplotlib + seaborn 生成 4 类图表

使用前请安装依赖：
    pip install cloudscraper beautifulsoup4 pandas matplotlib seaborn numpy lxml
================================================================================
"""

import os
import re
import sys
import time
import json
import random
import warnings
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

# ---------- matplotlib 全局设置 ----------
import matplotlib
matplotlib.use("Agg")  # 非交互式后端，避免无 GUI 环境报错
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

warnings.filterwarnings("ignore")

# 设置 seaborn 样式
sns.set_style("whitegrid")
sns.set_context("notebook", font_scale=1.1)

# ============================================================================
#  0.  全局配置
# ============================================================================

# --- 请求伪装 ---
HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://tianqi.moji.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

# --- 爬虫延迟（秒）---
DELAY_RANGE: Tuple[float, float] = (1.5, 3.5)
TIMEOUT: int = 20
MAX_RETRIES: int = 3

# --- 输出目录 ---
OUTPUT_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_output")

# --- 省份 ↔ 拼音 映射（用于构造 URL）---
# key=中文名, value=墨迹 URL 中使用的拼音
# 注意：墨迹对部分省份使用英文名而非拼音
PROVINCE_PINYIN: Dict[str, str] = {
    "北京": "beijing",
    "上海": "shanghai",
    "天津": "tianjin",
    "重庆": "chongqing",
    "河北": "hebei",
    "山西": "shanxi",
    "内蒙古": "inner-mongolia",
    "辽宁": "liaoning",
    "吉林": "jilin",
    "黑龙江": "heilongjiang",
    "江苏": "jiangsu",
    "浙江": "zhejiang",
    "安徽": "anhui",
    "福建": "fujian",
    "江西": "jiangxi",
    "山东": "shandong",
    "河南": "henan",
    "湖北": "hubei",
    "湖南": "hunan",
    "广东": "guangdong",
    "广西": "guangxi",
    "海南": "hainan",
    "四川": "sichuan",
    "贵州": "guizhou",
    "云南": "yunnan",
    "西藏": "tibet",
    "陕西": "shaanxi",
    "甘肃": "gansu",
    "青海": "qinghai",
    "宁夏": "ningxia",
    "新疆": "xinjiang",
    "香港": "hong-kong",
    "澳门": "macau",
    "台湾": "taiwan",
}

# --- 各省份代表性城市（省会 / 首府 / 主要城市）---
PROVINCE_CITIES: Dict[str, List[str]] = {
    "北京": ["北京"],
    "上海": ["上海"],
    "天津": ["天津"],
    "重庆": ["重庆"],
    "河北": ["石家庄"],
    "山西": ["太原"],
    "内蒙古": ["呼和浩特"],
    "辽宁": ["沈阳"],
    "吉林": ["长春"],
    "黑龙江": ["哈尔滨"],
    "江苏": ["南京"],
    "浙江": ["杭州"],
    "安徽": ["合肥"],
    "福建": ["福州"],
    "江西": ["南昌"],
    "山东": ["济南"],
    "河南": ["郑州"],
    "湖北": ["武汉"],
    "湖南": ["长沙"],
    "广东": ["广州"],
    "广西": ["南宁"],
    "海南": ["海口"],
    "四川": ["成都"],
    "贵州": ["贵阳"],
    "云南": ["昆明"],
    "西藏": ["拉萨"],
    "陕西": ["西安"],
    "甘肃": ["兰州"],
    "青海": ["西宁"],
    "宁夏": ["银川"],
    "新疆": ["乌鲁木齐"],
    "香港": ["香港"],
    "澳门": ["澳门"],
    "台湾": ["台北"],
}

# 城市拼音（墨迹 URL 中使用，并非所有城市都用标准拼音）
CITY_PINYIN: Dict[str, str] = {
    "北京": "beijing",
    "上海": "shanghai",
    "天津": "tianjin",
    "重庆": "chongqing",
    "石家庄": "shijiazhuang",
    "太原": "taiyuan",
    "呼和浩特": "hohhot",
    "沈阳": "shenyang",
    "长春": "changchun",
    "哈尔滨": "harbin",
    "南京": "nanjing",
    "杭州": "hangzhou",
    "合肥": "hefei",
    "福州": "fuzhou",
    "南昌": "nanchang",
    "济南": "jinan",
    "郑州": "zhengzhou",
    "武汉": "wuhan",
    "长沙": "changsha",
    "广州": "guangzhou",
    "南宁": "nanning",
    "海口": "haikou",
    "成都": "chengdu",
    "贵阳": "guiyang",
    "昆明": "kunming",
    "拉萨": "lhasa",
    "西安": "xian",
    "兰州": "lanzhou",
    "西宁": "xining",
    "银川": "yinchuan",
    "乌鲁木齐": "urumqi",
    "香港": "eastern-district",
    "澳门": "macau",
    "台北": "taipei-city",
}

# --- 用于模拟热力地图的城市大致坐标（经度, 纬度）---
CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "北京": (116.4, 39.9),
    "上海": (121.5, 31.2),
    "天津": (117.2, 39.1),
    "重庆": (106.5, 29.6),
    "石家庄": (114.5, 38.0),
    "太原": (112.5, 37.9),
    "呼和浩特": (111.8, 40.8),
    "沈阳": (123.4, 41.8),
    "长春": (125.3, 43.9),
    "哈尔滨": (126.6, 45.8),
    "南京": (118.8, 32.1),
    "杭州": (120.2, 30.3),
    "合肥": (117.3, 31.9),
    "福州": (119.3, 26.1),
    "南昌": (115.9, 28.7),
    "济南": (117.0, 36.7),
    "郑州": (113.7, 34.8),
    "武汉": (114.3, 30.6),
    "长沙": (113.0, 28.2),
    "广州": (113.3, 23.1),
    "南宁": (108.4, 22.8),
    "海口": (110.3, 20.0),
    "成都": (104.1, 30.6),
    "贵阳": (106.7, 26.6),
    "昆明": (102.7, 25.0),
    "拉萨": (91.1, 29.6),
    "西安": (108.9, 34.3),
    "兰州": (103.8, 36.0),
    "西宁": (101.8, 36.6),
    "银川": (106.3, 38.5),
    "乌鲁木齐": (87.6, 43.8),
    "香港": (114.2, 22.3),
    "澳门": (113.5, 22.2),
    "台北": (121.5, 25.0),
}


# ============================================================================
#  1.  爬虫模块  —  请求 + 解析
# ============================================================================

def _random_delay() -> None:
    """随机延时，降低被封风险"""
    time.sleep(random.uniform(*DELAY_RANGE))


def _create_scraper() -> cloudscraper.CloudScraper:
    """创建 cloudscraper 实例（自动绕过 Cloudflare 防护）"""
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False,
            "desktop": True,
        },
        delay=5,  # 自动重试延迟
    )
    # 先访问首页获取 Cookie，后续请求成功率更高
    try:
        scraper.get("https://tianqi.moji.com/", timeout=TIMEOUT)
    except Exception:
        pass
    return scraper


def fetch_page(url: str, scraper: cloudscraper.CloudScraper) -> Optional[str]:
    """
    获取网页 HTML 文本，cloudscraper 自动处理 Cloudflare 验证。
    失败返回 None。
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = scraper.get(url, timeout=TIMEOUT)
            resp.encoding = "utf-8"

            if resp.status_code == 200:
                return resp.text
            elif resp.status_code in (403, 503):
                print(f"  [!] 被拦截 (HTTP {resp.status_code}, 第 {attempt} 次): {url}")
                time.sleep(5 * attempt)
            elif resp.status_code == 404:
                print(f"  [x] 404 页面不存在: {url}")
                return None
            else:
                print(f"  [!] HTTP {resp.status_code} (第 {attempt} 次尝试): {url}")
                time.sleep(2 * attempt)
        except Exception as e:
            print(f"  [!] 请求异常 (第 {attempt} 次尝试): {e}")
            time.sleep(3 * attempt)

    return None


def parse_weather_page(html: str, province: str, city: str) -> List[Dict[str, Any]]:
    """
    解析墨迹天气未来 7 日预报页面。

    支持两种页面结构：
    - 主页（3 日）：ul.days.clearfix > li[5]
    - forecast7（7 日）：.wea_list_seven li
    """
    soup = BeautifulSoup(html, "lxml")
    records: List[Dict[str, Any]] = []

    # ---- 策略 A: 7 日预报页面 .wea_list_seven > li ----
    day_items = soup.select(".wea_list_seven li")
    if day_items:
        for li in day_items:
            record = _parse_forecast7_item(li, province, city)
            if record:
                records.append(record)

    # ---- 策略 B: 主页结构 ul.days.clearfix ----
    if not records:
        for ul in soup.select("ul.days.clearfix"):
            record = _parse_mainpage_day(ul, province, city)
            if record:
                records.append(record)

    if not records:
        print(f"    [x] 未找到天气预报数据: {city}")

    # 去重
    seen = set()
    unique = []
    for r in records:
        if r["日期"] not in seen:
            seen.add(r["日期"])
            unique.append(r)
    return unique[:7]


def _parse_forecast7_item(li, province: str, city: str) -> Optional[Dict[str, Any]]:
    """解析 7 日预报页面中的一个 <li>"""
    tree = li.select_one(".tree")
    if not tree:
        return None
    high_el = tree.select_one("b")
    low_el = tree.select_one("strong")
    high = int(high_el.get_text(strip=True).replace("°", "")) if high_el else None
    low = int(low_el.get_text(strip=True).replace("°", "")) if low_el else None

    # 天气状况
    wea_texts = li.select(".wea")
    condition = ""
    if wea_texts:
        condition = wea_texts[0].get_text(strip=True)
    wea_imgs = li.select(".weai img")
    if not condition and wea_imgs:
        condition = wea_imgs[0].get("alt", "")

    # 日期：最后一个 .week 是 MM/DD
    week_spans = li.select(".week")
    date_str = week_spans[-1].get_text(strip=True) if week_spans else ""

    if not date_str:
        return None

    return {
        "省份": province,
        "城市": city,
        "日期": date_str,
        "天气状况": condition or "未知",
        "最高温(℃)": high,
        "最低温(℃)": low,
        "风力风向": "",
        "AQI指数": "",
    }


def _parse_mainpage_day(ul, province: str, city: str) -> Optional[Dict[str, Any]]:
    """解析主页中的一个 ul.days.clearfix"""
    lis = ul.find_all("li", recursive=False)
    if len(lis) < 5:
        return None

    # 日期
    a = lis[0].find("a")
    date_str = a.get_text(strip=True) if a else lis[0].get_text(strip=True)

    # 天气状况
    img = lis[1].find("img")
    weather = lis[1].get_text(" ", strip=True)
    condition = img.get("alt", "") if img else weather

    # 温度
    temp_text = lis[2].get_text(" ", strip=True)
    nums = re.findall(r"(-?\d+)", temp_text)
    high, low = None, None
    if len(nums) >= 2:
        ints = [int(n) for n in nums]
        high, low = max(ints), min(ints)

    # 风力风向
    wind_em = lis[3].find("em")
    wind_b = lis[3].find("b")
    wind_parts = []
    if wind_em:
        wind_parts.append(wind_em.get_text(strip=True))
    if wind_b:
        wind_parts.append(wind_b.get_text(strip=True))
    wind = " ".join(wind_parts)

    # AQI
    strong = lis[4].find("strong")
    aqi = strong.get_text(" ", strip=True).replace("\n", "").strip() if strong else ""

    return {
        "省份": province,
        "城市": city,
        "日期": date_str,
        "天气状况": condition,
        "最高温(℃)": high,
        "最低温(℃)": low,
        "风力风向": wind,
        "AQI指数": aqi,
    }


def construct_forecast7_url(province: str, city: str) -> Optional[str]:
    """
    构造墨迹天气 7 日预报页面 URL。
    统一格式: /forecast7/china/{province_pinyin}/{city_pinyin}
    """
    BASE = "https://tianqi.moji.com/forecast7/china"
    prov_py = PROVINCE_PINYIN.get(province)
    city_py = CITY_PINYIN.get(city)
    if not prov_py or not city_py:
        return None
    return f"{BASE}/{prov_py}/{city_py}"


def scrape_city_weather(
    province: str, city: str, scraper: cloudscraper.CloudScraper
) -> List[Dict[str, Any]]:
    """
    爬取单个城市未来 7 日天气。
    优先使用 forecast7 页面（7 天数据），若解析失败则回退到主页（3 天）。
    """
    # 尝试 7 日预报页面
    url7 = construct_forecast7_url(province, city)
    if not url7:
        print(f"    [x] 无法构造 URL: {province} - {city}")
        return []

    print(f"    -> {url7}")
    html = fetch_page(url7, scraper)

    if html:
        records = parse_weather_page(html, province, city)
        if len(records) >= 7:
            print(f"    [OK] {len(records)} 天: {city}")
            return records[:7]

    print(f"    [x] 7 日页解析失败（仅 {len(records) if html else 0} 天）")
    return []


def scrape_all_weather() -> pd.DataFrame:
    """爬取所有省份代表性城市的天气数据"""
    print("=" * 60)
    print("  开始爬取墨迹天气数据")
    print(f"  目标: {len(PROVINCE_CITIES)} 个省份/地区")
    print("=" * 60)

    scraper = _create_scraper()
    all_records: List[Dict[str, Any]] = []

    # 先请求首页暖机
    print("\n[*] 初始化爬虫（访问首页获取 Cookie）...")
    homepage = fetch_page("https://tianqi.moji.com/", scraper)
    if not homepage:
        print("[!] 网站无法访问，请检查网络连接。")
        return pd.DataFrame()
    print("[[OK]] 爬虫就绪\n")

    total = sum(len(cities) for cities in PROVINCE_CITIES.values())
    done = 0

    for province, cities in PROVINCE_CITIES.items():
        print(f"\n[{province}] ({len(cities)} 城市)")
        for city in cities:
            records = scrape_city_weather(province, city, scraper)
            all_records.extend(records)
            done += 1
            print(f"  进度: {done}/{total}")
            _random_delay()

        # 省份间更长延迟
        time.sleep(random.uniform(2, 4))

    if not all_records:
        print("\n[!] 未能爬取到任何数据。")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"\n[[OK]] 爬取完成！共 {len(df)} 条记录。")
    return df


# ============================================================================
#  2.  样本数据  —  当爬虫失败时的回退方案
# ============================================================================

def generate_sample_data() -> pd.DataFrame:
    """
    生成模拟天气样本数据，用于演示分析和可视化功能。
    当爬虫完全失败时自动调用此函数。
    """
    print("\n[*] 生成模拟样本数据...")

    # 基础天气状况，按季节分配权重（6月）
    weather_pool = [
        ("晴", 25), ("晴转多云", 20), ("多云", 20),
        ("阴", 10), ("小雨", 8), ("阵雨", 6),
        ("中雨", 4), ("雷阵雨", 3), ("多云转晴", 3), ("晴间多云", 1),
    ]
    weights = [w for _, w in weather_pool]
    weather_list = [w for w, _ in weather_pool]

    # 风力池
    wind_pool = [
        "南风 2级", "南风 3级", "东南风 2级", "东南风 3级",
        "西南风 2级", "西南风 3级", "东北风 2级", "东北风 3级",
        "北风 2级", "北风 3级", "东风 2级", "西风 2级",
        "南风 1级", "东南风 1级",
    ]

    today = datetime.now()
    records = []

    # 各地气候特点（用于生成更真实的温度）
    climate_zones = {
        "北京": ("北温带", 5), "上海": ("亚热带", 3), "天津": ("北温带", 5),
        "重庆": ("亚热带", 0), "石家庄": ("北温带", 4), "太原": ("北温带", 6),
        "呼和浩特": ("温带大陆", 8), "沈阳": ("北温带", 7), "长春": ("北温带", 9),
        "哈尔滨": ("北温带", 10), "南京": ("亚热带", 2), "杭州": ("亚热带", 1),
        "合肥": ("亚热带", 2), "福州": ("亚热带", 0), "南昌": ("亚热带", 1),
        "济南": ("北温带", 3), "郑州": ("北温带", 3), "武汉": ("亚热带", 1),
        "长沙": ("亚热带", 0), "广州": ("亚热带", -2), "南宁": ("亚热带", -1),
        "海口": ("热带", -4), "成都": ("亚热带", 1), "贵阳": ("亚热带", 2),
        "昆明": ("亚热带", 3), "拉萨": ("高原", 10), "西安": ("北温带", 3),
        "兰州": ("北温带", 6), "西宁": ("高原", 9), "银川": ("北温带", 7),
        "乌鲁木齐": ("温带大陆", 8), "香港": ("亚热带", -1), "澳门": ("亚热带", -1),
        "台北": ("亚热带", 0),
    }

    base_high = 32  # 6月基准高温
    base_low = 22  # 6月基准低温

    for province, cities in PROVINCE_CITIES.items():
        for city in cities:
            zone_info = climate_zones.get(city, ("亚热带", 0))
            offset = zone_info[1]

            for day in range(7):
                date_obj = today + timedelta(days=day)
                date_str = f"{date_obj.month}月{date_obj.day}日"

                # 每天随机波动
                day_variation = random.uniform(-3, 3)
                high = base_high - offset + day_variation
                low = base_low - offset - 2 + random.uniform(-2, 2)

                # 随机天气
                condition = random.choices(weather_list, weights=weights, k=1)[0]

                # 根据天气调整温度
                if "雨" in condition:
                    high -= random.uniform(2, 5)
                    low -= random.uniform(1, 3)

                # 随机风力
                wind = random.choice(wind_pool)

                # 随机 AQI
                aqi_val = random.randint(20, 120)
                if aqi_val <= 50:
                    aqi_label = f"{aqi_val} 优"
                elif aqi_val <= 100:
                    aqi_label = f"{aqi_val} 良"
                else:
                    aqi_label = f"{aqi_val} 轻度污染"

                records.append({
                    "省份": province,
                    "城市": city,
                    "日期": date_str,
                    "天气状况": condition,
                    "最高温(℃)": round(high, 1),
                    "最低温(℃)": round(low, 1),
                    "风力风向": wind,
                    "AQI指数": aqi_label,
                })

    df = pd.DataFrame(records)
    print(f"[[OK]] 样本数据生成完成: {len(df)} 条记录")
    return df


# ============================================================================
#  3.  数据存储  —  CSV 输出
# ============================================================================

def save_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """
    将 DataFrame 保存为 CSV 文件，使用 UTF-8 with BOM 编码，
    确保中文字符在 Excel 中可以正常打开。
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"[[OK]] CSV 已保存: {filepath}")
    print(f"    编码: UTF-8 with BOM (Excel 可直接打开)")


def save_summary_csv(summary_df: pd.DataFrame, filepath: str) -> None:
    """保存统计汇总到 CSV"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    summary_df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"[[OK]] 汇总 CSV 已保存: {filepath}")


# ============================================================================
#  4.  数据清洗
# ============================================================================

def clean_weather_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗天气数据：
    - 处理缺失值
    - 格式化温度字段为数值
    - 补充缺失的 AQI 信息
    - 统一日期格式
    """
    print("\n" + "=" * 60)
    print("  数据清洗")
    print("=" * 60)

    df = df.copy()

    # --- 删除完全为空的行 ---
    before = len(df)
    df = df.dropna(how="all")
    after = len(df)
    if before - after > 0:
        print(f"  删除了 {before - after} 行全空数据")

    # --- 确保温度字段为数值类型 ---
    for col in ["最高温(℃)", "最低温(℃)"]:
        if col not in df.columns:
            print(f"  [!] 缺少字段: {col}")
            continue
        # 处理非数值（如 "32℃" → 32）
        df[col] = df[col].apply(_clean_temperature)
        # 填充缺失值（用该列均值）
        missing = df[col].isna().sum()
        if missing > 0:
            mean_val = df[col].mean()
            df[col] = df[col].fillna(round(mean_val, 1))
            print(f"  填充了 {col} 的 {missing} 个缺失值 (均值: {mean_val:.1f})")

    # --- 格式化日期（统一为 "MM月DD日"）---
    if "日期" in df.columns:
        df["日期"] = df["日期"].apply(_format_date)
        print(f"  日期格式已统一")

    # --- 缺失天气状况填充 ---
    if "天气状况" in df.columns:
        missing_cond = df["天气状况"].isna().sum()
        if missing_cond > 0:
            df["天气状况"] = df["天气状况"].fillna("未知")
            print(f"  填充了 {missing_cond} 个缺失的天气状况")

    # --- 提取 AQI 数值 ---
    if "AQI指数" in df.columns:
        # 先提取数值部分
        df["AQI数值"] = df["AQI指数"].apply(_extract_aqi_number)
        missing_aqi = df["AQI数值"].isna().sum()
        if missing_aqi > 0 and missing_aqi < len(df):
            mean_aqi = int(df["AQI数值"].mean())
            df.loc[df["AQI数值"].isna(), "AQI数值"] = mean_aqi
            df.loc[df["AQI指数"].isna(), "AQI指数"] = f"{mean_aqi} 良"
            print(f"  填充了 {missing_aqi} 个缺失的 AQI 数据")

    print(f"\n[[OK]] 清洗完成，当前共 {len(df)} 条记录")

    # 输出数据概览
    print(f"\n数据预览 (前5行):")
    print(df.head().to_string())
    print(f"\n数据统计:")
    for col in ["最高温(℃)", "最低温(℃)"]:
        if col in df.columns:
            print(f"  {col}: 均值={df[col].mean():.1f}, "
                  f"最大={df[col].max():.1f}, 最小={df[col].min():.1f}")

    return df


def _clean_temperature(val) -> Optional[float]:
    """将温度值转为 float"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    # 从字符串中提取数字
    s = str(val).strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1))
    return None


def _format_date(val) -> str:
    """统一日期格式为 'MM月DD日'"""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    # 已经是 MM月DD日 格式
    if re.match(r"\d{1,2}月\d{1,2}日", s):
        return s
    # 处理 YYYY-MM-DD
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{int(m.group(2))}月{int(m.group(3))}日"
    # 处理 M/D
    m = re.match(r"(\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{int(m.group(1))}月{int(m.group(2))}日"
    return s


def _extract_aqi_number(val) -> Optional[float]:
    """从 AQI 字段中提取数值"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    m = re.search(r"(\d+)", s)
    if m:
        return float(m.group(1))
    return None


# ============================================================================
#  5.  数据分析
# ============================================================================

def analyze_by_province(df: pd.DataFrame) -> pd.DataFrame:
    """
    按省份分组分析：
    - 平均最高温 / 平均最低温
    - 主要天气状况分布
    - 找出气温最高的城市
    """
    print("\n" + "=" * 60)
    print("  数据分析 — 按省份分组统计")
    print("=" * 60)

    # --- 5a. 各省平均气温 ---
    print("\n--- 各省份未来 7 日平均气温 ---")
    temp_stats = df.groupby("省份").agg(
        平均最高温=("最高温(℃)", "mean"),
        平均最低温=("最低温(℃)", "mean"),
    ).round(1).reset_index()
    temp_stats["平均日较差"] = (
        temp_stats["平均最高温"] - temp_stats["平均最低温"]
    ).round(1)
    temp_stats = temp_stats.sort_values("平均最高温", ascending=False)
    print(temp_stats.to_string(index=False))

    # --- 5b. 各省主要天气状况 ---
    print("\n--- 各省主要天气状况分布 ---")
    # 获取每个省份出现频率最高的天气
    weather_mode = (
        df.groupby("省份")["天气状况"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "未知")
        .reset_index()
        .rename(columns={"天气状况": "主要天气"})
    )
    # 计算主要天气占比
    total_by_province = df.groupby("省份").size().reset_index(name="总天数")
    weather_counts = (
        df.groupby(["省份", "天气状况"])
        .size()
        .reset_index(name="天数")
    )
    # 取每个省份最多的天气
    weather_top = weather_counts.loc[
        weather_counts.groupby("省份")["天数"].idxmax()
    ].reset_index(drop=True)
    weather_top["占比(%)"] = (
        weather_top["天数"]
        / weather_top.merge(total_by_province, on="省份")["总天数"]
        * 100
    ).round(1)
    weather_top = weather_top.rename(
        columns={"天气状况": "主要天气", "天数": "出现天数"}
    )
    print(weather_top[["省份", "主要天气", "出现天数", "占比(%)"]].to_string(index=False))

    # --- 5c. 全国气温最高的城市 ---
    print("\n--- 全国未来 7 日气温最高的城市 ---")
    city_max_temp = (
        df.groupby(["省份", "城市"])["最高温(℃)"]
        .max()
        .reset_index()
        .sort_values("最高温(℃)", ascending=False)
    )
    top_cities = city_max_temp.head(10)
    print("Top 10 高温城市:")
    print(top_cities.to_string(index=False))

    hottest = city_max_temp.iloc[0]
    print(f"\n[冠军] 全国未来 7 日气温最高的城市: {hottest['城市']} "
          f"({hottest['省份']}) — 最高温 {hottest['最高温(℃)']}℃")

    # --- 保存汇总 ---
    summary_path = os.path.join(OUTPUT_DIR, "province_temp_summary.csv")
    save_summary_csv(temp_stats, summary_path)

    return temp_stats


def analyze_weather_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """统计每种天气状况的总体占比"""
    print("\n--- 天气状况总体分布 ---")
    # value_counts 返回的 Series 列名可能与原列名相同，需显式重命名
    counts = df["天气状况"].value_counts().reset_index()
    counts.columns = ["天气状况", "天数"]  # 显式命名避免列名冲突
    counts["占比(%)"] = (counts["天数"] / counts["天数"].sum() * 100).round(1)
    print(counts.to_string(index=False))
    return counts


# ============================================================================
#  6.  可视化
# ============================================================================

def _setup_chinese_font() -> Optional[str]:
    """
    设置中文字体。
    返回字体名称，如果找不到合适字体则返回 None。
    """
    # Windows 常见中文字体路径
    win_font_candidates = [
        ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
        ("C:/Windows/Fonts/msyh.ttf", "Microsoft YaHei"),
        ("C:/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
        ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
        ("C:/Windows/Fonts/simfang.ttf", "FangSong"),
        ("C:/Windows/Fonts/simkai.ttf", "KaiTi"),
        ("C:/Windows/Fonts/SIMYOU.TTF", "YouYuan"),
        ("C:/Windows/Fonts/STHUPO.TTF", "STHupo"),
    ]

    # 1) 按路径查找
    for font_path, font_name in win_font_candidates:
        if os.path.exists(font_path):
            try:
                font_prop = fm.FontProperties(fname=font_path)
                # 注册字体
                fm.fontManager.addfont(font_path)
                print(f"  使用字体: {font_name} ({font_path})")
                return font_path
            except Exception:
                continue

    # 2) 按名称查找系统字体
    system_fonts = [f.name for f in fm.fontManager.ttflist]
    for preferred in ["SimHei", "Microsoft YaHei", "SimSun", "FangSong",
                       "Arial Unicode MS", "STHeiti", "WenQuanYi Micro Hei"]:
        matches = [f for f in system_fonts if preferred.lower() in f.lower()]
        if matches:
            print(f"  使用系统字体: {matches[0]}")
            return matches[0]

    print("  [!] 未找到中文字体，图表中的中文可能显示为方框。")
    print("    可手动安装: pip install matplotlib[fonts] 或安装中文字体。")
    return None


def _get_font_prop(font_path: Optional[str]):
    """获取字体属性对象"""
    if font_path and os.path.exists(font_path):
        return fm.FontProperties(fname=font_path)
    return None


def plot_temp_comparison(
    summary_df: pd.DataFrame, font_path: Optional[str] = None
) -> str:
    """
    图表1：各省平均气温对比条形图
    展示各省未来 7 日平均最高温与平均最低温。
    """
    print("\n--- 生成图表1: 各省平均气温对比条形图 ---")

    fp = _get_font_prop(font_path)
    fig, ax = plt.subplots(figsize=(16, 8))

    df_plot = summary_df.sort_values("平均最高温", ascending=True)

    x = df_plot["省份"]
    y1 = df_plot["平均最高温"]
    y2 = df_plot["平均最低温"]

    bar_width = 0.35
    x_pos = np.arange(len(x))

    bars1 = ax.bar(
        x_pos - bar_width / 2, y1, bar_width,
        label="平均最高温", color="#E74C3C", alpha=0.85, edgecolor="white", linewidth=0.5
    )
    bars2 = ax.bar(
        x_pos + bar_width / 2, y2, bar_width,
        label="平均最低温", color="#3498DB", alpha=0.85, edgecolor="white", linewidth=0.5
    )

    # 数值标签
    for bar in bars1:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 0.3,
            f"{h:.1f}", ha="center", va="bottom", fontsize=7,
            fontproperties=fp
        )
    for bar in bars2:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 0.3,
            f"{h:.1f}", ha="center", va="bottom", fontsize=7,
            fontproperties=fp
        )

    ax.set_xlabel("省份", fontsize=12, fontproperties=fp)
    ax.set_ylabel("温度 (℃)", fontsize=12, fontproperties=fp)
    ax.set_title("各省份未来 7 日平均气温对比", fontsize=16, fontweight="bold", fontproperties=fp)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x, rotation=45, ha="right", fontsize=9, fontproperties=fp)
    ax.legend(fontsize=11, prop=fp)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "01_avg_temp_comparison.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


def plot_temperature_heatmap(
    df: pd.DataFrame, font_path: Optional[str] = None
) -> str:
    """
    图表2：全国气温热力地图（模拟地理坐标）
    使用城市模拟经纬度绘制散点图，颜色表示气温高低。
    """
    print("\n--- 生成图表2: 全国气温热力地图（模拟坐标） ---")

    fp = _get_font_prop(font_path)
    fig, ax = plt.subplots(figsize=(14, 10))

    # 计算各城市平均最高温
    city_avg = (
        df.groupby(["省份", "城市"])["最高温(℃)"]
        .mean()
        .round(1)
        .reset_index()
    )

    # 获取坐标
    lons, lats, temps, labels = [], [], [], []
    for _, row in city_avg.iterrows():
        city = row["城市"]
        coords = CITY_COORDS.get(city)
        if coords:
            lons.append(coords[0])
            lats.append(coords[1])
            temps.append(row["最高温(℃)"])
            labels.append(city)

    if not lons:
        print("  [!] 无坐标数据，跳过热力地图")
        plt.close(fig)
        return ""

    # 散点图
    scatter = ax.scatter(
        lons, lats, c=temps, cmap="RdYlGn_r",
        s=180, alpha=0.8, edgecolors="gray", linewidth=0.8,
        vmin=min(temps) - 2, vmax=max(temps) + 2,
    )

    # 城市标签
    for lon, lat, label, temp in zip(lons, lats, labels, temps):
        ax.annotate(
            f"{label}\n{temp}℃",
            (lon, lat),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center", va="bottom",
            fontsize=7.5,
            fontproperties=fp,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85),
        )

    # 简易中国地图轮廓（模拟经纬度边界）
    ax.set_xlim(80, 130)
    ax.set_ylim(18, 55)

    # 添加颜色条
    cbar = plt.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("平均最高温 (℃)", fontsize=12, fontproperties=fp)

    ax.set_xlabel("经度", fontsize=12, fontproperties=fp)
    ax.set_ylabel("纬度", fontsize=12, fontproperties=fp)
    ax.set_title("全国主要城市气温热力分布（模拟坐标）",
                 fontsize=16, fontweight="bold", fontproperties=fp)
    ax.grid(True, alpha=0.3)

    # 添加方位标识
    ax.text(0.02, 0.98, "N", transform=ax.transAxes, fontsize=20,
            fontweight="bold", va="top", color="gray")

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "02_temp_heatmap.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


def plot_temp_trends(df: pd.DataFrame, font_path: Optional[str] = None) -> str:
    """
    图表3：代表性城市 7 日气温趋势折线图
    从各大区选取代表性城市展示。
    """
    print("\n--- 生成图表3: 城市 7 日气温趋势折线图 ---")

    representative_cities = [
        "北京", "上海", "广州", "成都",
        "哈尔滨", "乌鲁木齐", "拉萨", "武汉",
    ]

    # 过滤数据
    plot_df = df[df["城市"].isin(representative_cities)].copy()
    if plot_df.empty:
        print("  [!] 无代表性城市数据，跳过趋势图")
        return ""

    # 排序日期
    plot_df["日期序号"] = plot_df["日期"].apply(
        lambda x: int(re.search(r"(\d+)", x).group(1)) if re.search(r"(\d+)", x) else 0
    )
    plot_df = plot_df.sort_values(["城市", "日期序号"])

    fp = _get_font_prop(font_path)
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()

    colors_high = "#E74C3C"
    colors_low = "#3498DB"

    for i, city in enumerate(representative_cities):
        ax = axes[i]
        city_data = plot_df[plot_df["城市"] == city]

        if city_data.empty:
            ax.text(0.5, 0.5, "无数据", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, fontproperties=fp)
            ax.set_title(city, fontsize=13, fontweight="bold", fontproperties=fp)
            continue

        dates = city_data["日期"].tolist()
        highs = city_data["最高温(℃)"].tolist()
        lows = city_data["最低温(℃)"].tolist()

        x_pos = range(len(dates))

        ax.plot(x_pos, highs, "o-", color=colors_high, linewidth=2.2,
                markersize=7, label="最高温", zorder=3)
        ax.plot(x_pos, lows, "s-", color=colors_low, linewidth=2.2,
                markersize=7, label="最低温", zorder=3)

        # 填充区域
        ax.fill_between(x_pos, highs, lows, alpha=0.1, color="#9B59B6")

        # 数值标签
        for j, (h, l) in enumerate(zip(highs, lows)):
            ax.annotate(f"{h}°", (j, h), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8,
                        color=colors_high, fontweight="bold")
            ax.annotate(f"{l}°", (j, l), textcoords="offset points",
                        xytext=(0, -12), ha="center", fontsize=8,
                        color=colors_low, fontweight="bold")

        ax.set_title(city, fontsize=13, fontweight="bold", fontproperties=fp)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(dates, rotation=30, ha="right", fontsize=8, fontproperties=fp)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, prop=fp, loc="best")

    fig.suptitle(
        "代表性城市未来 7 日气温变化趋势",
        fontsize=18, fontweight="bold", y=1.02, fontproperties=fp
    )
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "03_temp_trends.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


def plot_weather_pie_chart(df: pd.DataFrame, font_path: Optional[str] = None) -> str:
    """
    图表4：天气状况饼图
    展示各省主要天气类型占比（选取前 8 个省份）。
    """
    print("\n--- 生成图表4: 天气状况饼图 ---")

    fp = _get_font_prop(font_path)

    # 选取前 8 个省份（按数据量）
    top_provinces = df["省份"].value_counts().head(8).index.tolist()

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()

    # 颜色方案
    colors = plt.cm.Set3(np.linspace(0, 1, 10))

    for i, province in enumerate(top_provinces):
        ax = axes[i]
        prov_data = df[df["省份"] == province]

        # 天气状况分布
        weather_dist = prov_data["天气状况"].value_counts()
        # 合并小类别为"其他"
        threshold = 0.05 * weather_dist.sum()
        main = weather_dist[weather_dist >= threshold]
        other = weather_dist[weather_dist < threshold]
        if not other.empty:
            main["其他"] = other.sum()

        wedges, texts, autotexts = ax.pie(
            main.values,
            labels=main.index,
            autopct="%1.0f%%",
            colors=colors[: len(main)],
            startangle=90,
            pctdistance=0.75,
            wedgeprops={"edgecolor": "white", "linewidth": 0.8},
            textprops={"fontsize": 8},
        )

        # 设置标签字体
        for t in texts:
            if fp:
                t.set_fontproperties(fp)
        for t in autotexts:
            t.set_fontsize(8)

        ax.set_title(province, fontsize=14, fontweight="bold", fontproperties=fp)

    fig.suptitle(
        "各省份主要天气类型分布（前 8 省）",
        fontsize=18, fontweight="bold", y=1.02, fontproperties=fp
    )
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "04_weather_pie_chart.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


# ============================================================================
#  7.  主流程
# ============================================================================

def run_pipeline(use_sample: bool = False) -> None:
    """
    主流程：爬取 → 存储 → 清洗 → 分析 → 可视化

    Args:
        use_sample: 若为 True，则跳过爬虫直接使用样本数据
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start_time = datetime.now()
    print(f"\n{'=' * 60}")
    print(f"  天气数据分析系统")
    print(f"  启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    # ========== 阶段一：数据获取 ==========
    print("\n" + "-" * 30)
    print("  阶段一：数据获取")
    print("-" * 30)

    if not use_sample:
        df_raw = scrape_all_weather()
        if df_raw.empty:
            print("\n[!] 错误：爬虫未获取到任何数据，请检查网络连接或网站是否可访问。")
            print("    可使用 --sample 参数运行示例模式。")
            sys.exit(1)
        else:
            print("\n[[OK]] 成功从墨迹天气获取数据！")
    else:
        print("[*] 使用样本数据模式（仅用于演示分析和可视化功能）。")
        df_raw = generate_sample_data()

    # ========== 阶段二：数据存储 ==========
    print("\n" + "-" * 30)
    print("  阶段二：数据存储")
    print("-" * 30)

    csv_path = os.path.join(OUTPUT_DIR, "weather_data.csv")
    save_to_csv(df_raw, csv_path)

    # ========== 阶段三：数据清洗 ==========
    print("\n" + "-" * 30)
    print("  阶段三：数据清洗与整理")
    print("-" * 30)

    df_clean = clean_weather_data(df_raw)

    # 保存清洗后数据
    clean_csv_path = os.path.join(OUTPUT_DIR, "weather_data_clean.csv")
    save_to_csv(df_clean, clean_csv_path)

    # ========== 阶段四：数据分析 ==========
    print("\n" + "-" * 30)
    print("  阶段四：数据分析")
    print("-" * 30)

    summary = analyze_by_province(df_clean)
    weather_dist = analyze_weather_distribution(df_clean)

    # ========== 阶段五：数据可视化 ==========
    print("\n" + "-" * 30)
    print("  阶段五：数据可视化")
    print("-" * 30)

    font_path = _setup_chinese_font()

    paths = []
    paths.append(plot_temp_comparison(summary, font_path))
    paths.append(plot_temperature_heatmap(df_clean, font_path))
    paths.append(plot_temp_trends(df_clean, font_path))
    paths.append(plot_weather_pie_chart(df_clean, font_path))

    # ========== 完成 ==========
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 60)
    print(f"  [完成] 全流程完成！耗时: {elapsed:.1f} 秒")
    print("=" * 60)
    print(f"\n输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print(f"  CSV 数据: weather_data.csv / weather_data_clean.csv")
    print(f"  统计汇总: province_temp_summary.csv")
    print(f"  可视化图表:")
    chart_names = [
        "01_avg_temp_comparison.png  — 各省平均气温对比条形图",
        "02_temp_heatmap.png         — 全国气温热力地图",
        "03_temp_trends.png          — 城市 7 日气温趋势折线图",
        "04_weather_pie_chart.png    — 天气状况饼图",
    ]
    for name in chart_names:
        print(f"    {name}")

    # 统计文件大小
    print(f"\n输出文件大小:")
    for f in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  {f}: {size_kb:.1f} KB")


# ============================================================================
#  8.  命令行入口
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="天气数据分析系统 — 爬虫 + 分析 + 可视化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python weather_analysis.py              # 正常模式（爬虫 → 分析）\n"
            "  python weather_analysis.py --sample     # 使用样本数据（跳过爬虫）\n"
            "  python weather_analysis.py --output ./my_output  # 指定输出目录\n"
        ),
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="使用样本数据模式（跳过爬虫，直接生成模拟数据）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=OUTPUT_DIR,
        help=f"输出目录（默认: {OUTPUT_DIR}）",
    )

    args = parser.parse_args()

    OUTPUT_DIR = os.path.abspath(args.output)

    banner = """
+==========================================+
|        [天气] 天气数据分析系统  v1.0       |
|                                          |
|  爬取源: 墨迹天气 (tianqi.moji.com)      |
|  功能: 爬取 -> 存储 -> 清洗 -> 分析 -> 图表 |
+==========================================+
    """
    # 兼容 Windows GBK 终端
    safe_banner = banner.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8"
    )
    print(safe_banner)

    run_pipeline(use_sample=args.sample)
