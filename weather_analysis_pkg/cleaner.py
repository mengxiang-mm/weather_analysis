"""
┌────────────────────────────────────────────────────────────┐
│  数据清洗模块 — 缺失值处理 / 格式统一 / 类型转换            │
└────────────────────────────────────────────────────────────┘
"""

import os
import re
from typing import Optional

import pandas as pd

from . import config


# ============================================================
#  1.  存储
# ============================================================

def save_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """保存为 CSV（UTF-8 with BOM，Excel 可直接打开）"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"[[OK]] CSV 已保存: {filepath}")


def save_summary_csv(summary_df: pd.DataFrame, filepath: str) -> None:
    """保存统计汇总到 CSV"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    summary_df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"[[OK]] 汇总 CSV 已保存: {filepath}")


# ============================================================
#  2.  清洗
# ============================================================

def clean_weather_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗天气数据：
    - 删除全空行
    - 温度字段转数值
    - 统一日期格式
    - 填充缺失天气/AQI
    """
    print("\n" + "=" * 60)
    print("  数据清洗")
    print("=" * 60)

    df = df.copy()

    # 删除全空行
    before = len(df)
    df = df.dropna(how="all")
    if len(df) < before:
        print(f"  删除了 {before - len(df)} 行全空数据")

    # 温度字段转数值
    for col in ["最高温(℃)", "最低温(℃)"]:
        if col not in df.columns:
            print(f"  [!] 缺少字段: {col}")
            continue
        df[col] = df[col].apply(_clean_temperature)
        missing = df[col].isna().sum()
        if missing > 0:
            mean_val = df[col].mean()
            df[col] = df[col].fillna(round(mean_val, 1))
            print(f"  填充了 {col} 的 {missing} 个缺失值 (均值: {mean_val:.1f})")

    # 统一日期
    if "日期" in df.columns:
        df["日期"] = df["日期"].apply(_format_date)

    # 填充天气
    if "天气状况" in df.columns:
        missing_cond = df["天气状况"].isna().sum()
        if missing_cond > 0:
            df["天气状况"] = df["天气状况"].fillna("未知")
            print(f"  填充了 {missing_cond} 个缺失的天气状况")

    # AQI 提取
    if "AQI指数" in df.columns:
        df["AQI数值"] = df["AQI指数"].apply(_extract_aqi_number)
        missing_aqi = df["AQI数值"].isna().sum()
        if missing_aqi > 0 and missing_aqi < len(df):
            mean_aqi = int(df["AQI数值"].mean())
            df.loc[df["AQI数值"].isna(), "AQI数值"] = mean_aqi
            df.loc[df["AQI指数"].isna(), "AQI指数"] = f"{mean_aqi} 良"
            print(f"  填充了 {missing_aqi} 个缺失的 AQI 数据")

    print(f"\n[[OK]] 清洗完成，当前共 {len(df)} 条记录")

    # 概览
    print(f"\n数据预览 (前5行):")
    print(df.head().to_string())
    print(f"\n数据统计:")
    for col in ["最高温(℃)", "最低温(℃)"]:
        if col in df.columns:
            print(f"  {col}: 均值={df[col].mean():.1f}, "
                  f"最大={df[col].max():.1f}, 最小={df[col].min():.1f}")

    return df


# ============================================================
#  3.  字段处理函数
# ============================================================

def _clean_temperature(val) -> Optional[float]:
    """温度值转 float：'32℃' → 32.0, '32℃/23℃' → 32.0"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def _format_date(val) -> str:
    """统一日期格式为 'MM月DD日'"""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if re.match(r"\d{1,2}月\d{1,2}日", s):
        return s
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{int(m.group(2))}月{int(m.group(3))}日"
    m = re.match(r"(\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{int(m.group(1))}月{int(m.group(2))}日"
    return s


def _extract_aqi_number(val) -> Optional[float]:
    """从 AQI 字段提取数值：'78 良' → 78.0"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    m = re.search(r"(\d+)", s)
    return float(m.group(1)) if m else None
