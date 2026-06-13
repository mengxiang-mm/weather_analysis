"""
┌────────────────────────────────────────────────────────────┐
│  配置模块 — 从 province_data.json 加载共享数据              │
│  单例模式：import 时自动加载，模块内全局可用                  │
└────────────────────────────────────────────────────────────┘
"""

import json
import os
from typing import Dict, List, Tuple, Optional, Any

# ── 路径 ──────────────────────────────────────────────────
PKG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PKG_DIR)
DATA_FILE = os.path.join(PROJECT_DIR, "province_data.json")
OUTPUT_DIR: str = os.path.join(PROJECT_DIR, "weather_output")

# ── 爬虫配置 ──────────────────────────────────────────────
DELAY_RANGE: Tuple[float, float] = (1.5, 3.5)
TIMEOUT: int = 20
MAX_RETRIES: int = 3

# ── User-Agent 池（轮换使用，降低被识别概率） ──────────────
USER_AGENTS: List[str] = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]

# ── 基础请求头（不包含 UA，UA 会动态轮换） ─────────────────
BASE_HEADERS: Dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://tianqi.moji.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

# ── 缓存（懒加载） ────────────────────────────────────────
_cache: Dict[str, Any] = {}


def _load_json() -> dict:
    """加载 province_data.json（带缓存）"""
    if "data" not in _cache:
        if not os.path.exists(DATA_FILE):
            raise FileNotFoundError(
                f"共享数据文件不存在: {DATA_FILE}\n"
                f"请确保 province_data.json 位于项目根目录。"
            )
        with open(DATA_FILE, encoding="utf-8") as f:
            _cache["data"] = json.load(f)
    return _cache["data"]


def get_provinces() -> List[dict]:
    """获取省份列表 (每个元素含 region/name/city/provincePinyin/cityPinyin)"""
    return _load_json()["provinces"]


def get_regions() -> List[str]:
    """获取地区（大区）列表"""
    return _load_json()["regions"]


def get_city_coords() -> Dict[str, List[float]]:
    """获取城市坐标 {城市名: [经度, 纬度]}"""
    return _load_json()["cityCoords"]


# ── 兼容旧代码的映射字典 ──────────────────────────────────
def _build_maps() -> tuple:
    """从统一数据构建旧式映射字典"""
    prov_pinyin: Dict[str, str] = {}
    prov_cities: Dict[str, List[str]] = {}
    city_pinyin: Dict[str, str] = {}
    city_coords: Dict[str, Tuple[float, float]] = {}

    for p in get_provinces():
        prov_pinyin[p["name"]] = p["provincePinyin"]
        prov_cities.setdefault(p["name"], []).append(p["city"])
        city_pinyin[p["city"]] = p["cityPinyin"]

    for city, coord in get_city_coords().items():
        city_coords[city] = (coord[0], coord[1])

    return prov_pinyin, prov_cities, city_pinyin, city_coords


# 向后兼容：模块级常量，import config 即可使用
PROVINCE_PINYIN: Dict[str, str] = {}
PROVINCE_CITIES: Dict[str, List[str]] = {}
CITY_PINYIN: Dict[str, str] = {}
CITY_COORDS: Dict[str, Tuple[float, float]] = {}

def _init_maps():
    global PROVINCE_PINYIN, PROVINCE_CITIES, CITY_PINYIN, CITY_COORDS
    PROVINCE_PINYIN, PROVINCE_CITIES, CITY_PINYIN, CITY_COORDS = _build_maps()

_init_maps()
