"""
┌────────────────────────────────────────────────────────────┐
│  数据分析模块 — 分组统计 / 天气分布 / 极值分析              │
└────────────────────────────────────────────────────────────┘
"""

import os
import pandas as pd

from . import config
from .cleaner import save_summary_csv


def analyze_by_province(df: pd.DataFrame) -> pd.DataFrame:
    """按省份分组分析：平均气温 + 天气分布 + 高温排行"""
    print("\n" + "=" * 60)
    print("  数据分析 — 按省份分组统计")
    print("=" * 60)

    # --- 各省平均气温 ---
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

    # --- 主要天气状况 ---
    print("\n--- 各省主要天气状况分布 ---")
    weather_mode = (
        df.groupby("省份")["天气状况"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "未知")
        .reset_index()
        .rename(columns={"天气状况": "主要天气"})
    )
    total_by_province = df.groupby("省份").size().reset_index(name="总天数")
    weather_counts = (
        df.groupby(["省份", "天气状况"]).size().reset_index(name="天数")
    )
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

    # --- 高温前十城市 ---
    print("\n--- 全国未来 7 日气温最高的城市 ---")
    city_max_temp = (
        df.groupby(["省份", "城市"])["最高温(℃)"]
        .max().reset_index()
        .sort_values("最高温(℃)", ascending=False)
    )
    print("Top 10 高温城市:")
    print(city_max_temp.head(10).to_string(index=False))

    hottest = city_max_temp.iloc[0]
    print(f"\n[冠军] {hottest['城市']} ({hottest['省份']}) — 最高温 {hottest['最高温(℃)']}℃")

    # 保存
    summary_path = os.path.join(config.OUTPUT_DIR, "province_temp_summary.csv")
    save_summary_csv(temp_stats, summary_path)

    return temp_stats


def analyze_weather_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """统计每种天气状况的总体占比"""
    print("\n--- 天气状况总体分布 ---")
    counts = df["天气状况"].value_counts().reset_index()
    counts.columns = ["天气状况", "天数"]
    counts["占比(%)"] = (counts["天数"] / counts["天数"].sum() * 100).round(1)
    print(counts.to_string(index=False))
    return counts
