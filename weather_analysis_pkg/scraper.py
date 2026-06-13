"""
┌────────────────────────────────────────────────────────────┐
│  爬虫模块 — 墨迹天气数据抓取                                │
│  功能：请求伪装 → 获取页面 → 解析 HTML → 结构化数据         │
└────────────────────────────────────────────────────────────┘
"""

import random
import time
import re
from typing import List, Dict, Optional, Any, Tuple

import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd

from . import config


# ============================================================
#  1.  网络请求
# ============================================================

def _random_headers() -> Dict[str, str]:
    """生成带随机 User-Agent 的请求头"""
    headers = dict(config.BASE_HEADERS)
    headers["User-Agent"] = random.choice(config.USER_AGENTS)
    return headers


def _random_delay() -> None:
    """随机延时，降低被封风险"""
    time.sleep(random.uniform(*config.DELAY_RANGE))


def _create_scraper() -> cloudscraper.CloudScraper:
    """创建 cloudscraper 实例（自动绕过 Cloudflare 防护）"""
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False,
            "desktop": True,
        },
        delay=5,
    )
    # 设置随机 UA
    scraper.headers.update(_random_headers())
    # 首页暖机获取 Cookie
    try:
        scraper.get("https://tianqi.moji.com/", timeout=config.TIMEOUT)
    except Exception:
        pass
    return scraper


def fetch_page(url: str, scraper: cloudscraper.CloudScraper) -> Optional[str]:
    """
    获取网页 HTML 文本，cloudscraper 自动处理 Cloudflare 验证。
    每次请求前轮换 UA，失败返回 None。
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            # 每次请求轮换 UA
            scraper.headers.update(_random_headers())

            resp = scraper.get(url, timeout=config.TIMEOUT)
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


# ============================================================
#  2.  HTML 解析
# ============================================================

def parse_weather_page(html: str, province: str, city: str) -> List[Dict[str, Any]]:
    """
    解析墨迹天气未来 7 日预报页面。
    支持两种页面结构：
    - 7日页 .wea_list_seven li
    - 主页 ul.days.clearfix > li
    """
    soup = BeautifulSoup(html, "lxml")
    records: List[Dict[str, Any]] = []

    # 策略 A: 7 日预报页面
    day_items = soup.select(".wea_list_seven li")
    if day_items:
        for li in day_items:
            record = _parse_forecast7_item(li, province, city)
            if record:
                records.append(record)

    # 策略 B: 主页结构
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

    wea_texts = li.select(".wea")
    condition = ""
    if wea_texts:
        condition = wea_texts[0].get_text(strip=True)
    wea_imgs = li.select(".weai img")
    if not condition and wea_imgs:
        condition = wea_imgs[0].get("alt", "")

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

    a = lis[0].find("a")
    date_str = a.get_text(strip=True) if a else lis[0].get_text(strip=True)

    img = lis[1].find("img")
    weather = lis[1].get_text(" ", strip=True)
    condition = img.get("alt", "") if img else weather

    temp_text = lis[2].get_text(" ", strip=True)
    nums = re.findall(r"(-?\d+)", temp_text)
    high, low = None, None
    if len(nums) >= 2:
        ints = [int(n) for n in nums]
        high, low = max(ints), min(ints)

    wind_em = lis[3].find("em")
    wind_b = lis[3].find("b")
    wind_parts = []
    if wind_em:
        wind_parts.append(wind_em.get_text(strip=True))
    if wind_b:
        wind_parts.append(wind_b.get_text(strip=True))
    wind = " ".join(wind_parts)

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


# ============================================================
#  3.  URL 构造 & 爬取流程
# ============================================================

def construct_forecast7_url(province: str, city: str) -> Optional[str]:
    """构造墨迹天气 7 日预报页面 URL"""
    BASE = "https://tianqi.moji.com/forecast7/china"
    prov_py = config.PROVINCE_PINYIN.get(province)
    city_py = config.CITY_PINYIN.get(city)
    if not prov_py or not city_py:
        return None
    return f"{BASE}/{prov_py}/{city_py}"


def scrape_city_weather(
    province: str, city: str, scraper: cloudscraper.CloudScraper
) -> List[Dict[str, Any]]:
    """爬取单个城市未来 7 日天气"""
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

    print(f"    [x] 7 日页解析失败")
    return []


def scrape_all_weather() -> pd.DataFrame:
    """爬取所有省份代表性城市的天气数据"""
    print("=" * 60)
    print("  开始爬取墨迹天气数据")
    print(f"  目标: {len(config.PROVINCE_CITIES)} 个省份/地区")
    print("=" * 60)

    scraper = _create_scraper()
    all_records: List[Dict[str, Any]] = []

    print("\n[*] 初始化爬虫（访问首页获取 Cookie）...")
    homepage = fetch_page("https://tianqi.moji.com/", scraper)
    if not homepage:
        print("[!] 网站无法访问，请检查网络连接。")
        return pd.DataFrame()
    print("[[OK]] 爬虫就绪\n")

    total = sum(len(cities) for cities in config.PROVINCE_CITIES.values())
    done = 0

    for province, cities in config.PROVINCE_CITIES.items():
        print(f"\n[{province}] ({len(cities)} 城市)")
        for city in cities:
            records = scrape_city_weather(province, city, scraper)
            all_records.extend(records)
            done += 1
            print(f"  进度: {done}/{total}")
            _random_delay()

        time.sleep(random.uniform(2, 4))

    if not all_records:
        print("\n[!] 未能爬取到任何数据。")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"\n[[OK]] 爬取完成！共 {len(df)} 条记录。")
    return df


# ============================================================
#  4.  样本数据生成
# ============================================================

def generate_sample_data() -> pd.DataFrame:
    """
    生成模拟天气样本数据，用于演示分析和可视化功能。
    当爬虫失败或指定 --sample 时自动调用。
    """
    print("\n[*] 生成模拟样本数据...")

    weather_pool = [
        ("晴", 25), ("晴转多云", 20), ("多云", 20),
        ("阴", 10), ("小雨", 8), ("阵雨", 6),
        ("中雨", 4), ("雷阵雨", 3), ("多云转晴", 3), ("晴间多云", 1),
    ]
    weights = [w for _, w in weather_pool]
    weather_list = [w for w, _ in weather_pool]

    wind_pool = [
        "南风 2级", "南风 3级", "东南风 2级", "东南风 3级",
        "西南风 2级", "西南风 3级", "东北风 2级", "东北风 3级",
        "北风 2级", "北风 3级", "东风 2级", "西风 2级",
        "南风 1级", "东南风 1级",
    ]

    from datetime import datetime, timedelta
    today = datetime.now()
    records = []

    # 各地气候特点
    climate_zones = {
        "北京": 5, "上海": 3, "天津": 5, "重庆": 0,
        "石家庄": 4, "太原": 6, "呼和浩特": 8,
        "沈阳": 7, "长春": 9, "哈尔滨": 10,
        "南京": 2, "杭州": 1, "合肥": 2, "福州": 0,
        "南昌": 1, "济南": 3, "郑州": 3, "武汉": 1,
        "长沙": 0, "广州": -2, "南宁": -1, "海口": -4,
        "成都": 1, "贵阳": 2, "昆明": 3, "拉萨": 10,
        "西安": 3, "兰州": 6, "西宁": 9, "银川": 7,
        "乌鲁木齐": 8, "香港": -1, "澳门": -1, "台北": 0,
    }

    base_high = 32
    base_low = 22

    for province, cities in config.PROVINCE_CITIES.items():
        for city in cities:
            offset = climate_zones.get(city, 0)

            for day in range(7):
                date_obj = today + timedelta(days=day)
                date_str = f"{date_obj.month}月{date_obj.day}日"

                day_variation = random.uniform(-3, 3)
                high = base_high - offset + day_variation
                low = base_low - offset - 2 + random.uniform(-2, 2)

                condition = random.choices(weather_list, weights=weights, k=1)[0]

                if "雨" in condition:
                    high -= random.uniform(2, 5)
                    low -= random.uniform(1, 3)

                wind = random.choice(wind_pool)

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
