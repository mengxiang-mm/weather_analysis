"""
┌────────────────────────────────────────────────────────────┐
│  可视化模块 — 4 类统计图表生成                              │
│  依赖 matplotlib + seaborn，中文字体自动检测                │
└────────────────────────────────────────────────────────────┘
"""

import os
import re
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import seaborn as sns

from . import config


sns.set_style("whitegrid")
sns.set_context("notebook", font_scale=1.1)


# ============================================================
#  1.  字体管理
# ============================================================

def setup_chinese_font() -> Optional[str]:
    """
    自动检测中文字体。
    返回字体路径（或字体名称），None 表示未找到。
    """
    win_font_candidates = [
        ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
        ("C:/Windows/Fonts/msyh.ttf", "Microsoft YaHei"),
        ("C:/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
        ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
        ("C:/Windows/Fonts/simfang.ttf", "FangSong"),
        ("C:/Windows/Fonts/simkai.ttf", "KaiTi"),
        ("C:/Windows/Fonts/SIMYOU.TTF", "YouYuan"),
    ]

    for font_path, font_name in win_font_candidates:
        if os.path.exists(font_path):
            try:
                fm.fontManager.addfont(font_path)
                print(f"  使用字体: {font_name} ({font_path})")
                return font_path
            except Exception:
                continue

    system_fonts = [f.name for f in fm.fontManager.ttflist]
    for preferred in ["SimHei", "Microsoft YaHei", "SimSun",
                       "Arial Unicode MS", "STHeiti", "WenQuanYi Micro Hei"]:
        matches = [f for f in system_fonts if preferred.lower() in f.lower()]
        if matches:
            print(f"  使用系统字体: {matches[0]}")
            return matches[0]

    print("  [!] 未找到中文字体，图表中文可能显示为方框。")
    return None


def _get_font_prop(font_path: Optional[str]):
    if font_path and os.path.exists(font_path):
        return fm.FontProperties(fname=font_path)
    return None


# ============================================================
#  2.  图表函数
# ============================================================

def plot_temp_comparison(summary_df: pd.DataFrame, font_path: Optional[str] = None) -> str:
    """图表1：各省平均气温对比条形图"""
    print("\n--- 生成图表1: 各省平均气温对比条形图 ---")

    fp = _get_font_prop(font_path)
    fig, ax = plt.subplots(figsize=(16, 8))

    df_plot = summary_df.sort_values("平均最高温", ascending=True)

    x = df_plot["省份"]
    y1 = df_plot["平均最高温"]
    y2 = df_plot["平均最低温"]

    bar_width = 0.35
    x_pos = np.arange(len(x))

    bars1 = ax.bar(x_pos - bar_width / 2, y1, bar_width,
                   label="平均最高温", color="#E74C3C", alpha=0.85,
                   edgecolor="white", linewidth=0.5)
    bars2 = ax.bar(x_pos + bar_width / 2, y2, bar_width,
                   label="平均最低温", color="#3498DB", alpha=0.85,
                   edgecolor="white", linewidth=0.5)

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                f"{h:.1f}", ha="center", va="bottom", fontsize=7, fontproperties=fp)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                f"{h:.1f}", ha="center", va="bottom", fontsize=7, fontproperties=fp)

    ax.set_xlabel("省份", fontsize=12, fontproperties=fp)
    ax.set_ylabel("温度 (℃)", fontsize=12, fontproperties=fp)
    ax.set_title("各省份未来 7 日平均气温对比", fontsize=16, fontweight="bold", fontproperties=fp)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x, rotation=45, ha="right", fontsize=9, fontproperties=fp)
    ax.legend(fontsize=11, prop=fp)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    save_path = os.path.join(config.OUTPUT_DIR, "01_avg_temp_comparison.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


def plot_temperature_heatmap(df: pd.DataFrame, font_path: Optional[str] = None) -> str:
    """图表2：全国气温热力地图（模拟地理坐标）"""
    print("\n--- 生成图表2: 全国气温热力地图 ---")

    fp = _get_font_prop(font_path)
    fig, ax = plt.subplots(figsize=(14, 10))

    city_avg = (
        df.groupby(["省份", "城市"])["最高温(℃)"]
        .mean().round(1).reset_index()
    )

    coords = config.get_city_coords()
    lons, lats, temps, labels = [], [], [], []
    for _, row in city_avg.iterrows():
        city = row["城市"]
        coord = coords.get(city)
        if coord:
            lons.append(coord[0])
            lats.append(coord[1])
            temps.append(row["最高温(℃)"])
            labels.append(city)

    if not lons:
        print("  [!] 无坐标数据，跳过热力地图")
        plt.close(fig)
        return ""

    scatter = ax.scatter(
        lons, lats, c=temps, cmap="RdYlGn_r",
        s=180, alpha=0.8, edgecolors="gray", linewidth=0.8,
        vmin=min(temps) - 2, vmax=max(temps) + 2,
    )

    for lon, lat, label, temp in zip(lons, lats, labels, temps):
        ax.annotate(
            f"{label}\n{temp}℃",
            (lon, lat),
            textcoords="offset points",
            xytext=(0, 12), ha="center", va="bottom",
            fontsize=7.5, fontproperties=fp,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85),
        )

    ax.set_xlim(80, 130)
    ax.set_ylim(18, 55)

    cbar = plt.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("平均最高温 (℃)", fontsize=12, fontproperties=fp)

    ax.set_xlabel("经度", fontsize=12, fontproperties=fp)
    ax.set_ylabel("纬度", fontsize=12, fontproperties=fp)
    ax.set_title("全国主要城市气温热力分布（模拟坐标）",
                 fontsize=16, fontweight="bold", fontproperties=fp)
    ax.grid(True, alpha=0.3)
    ax.text(0.02, 0.98, "N", transform=ax.transAxes, fontsize=20,
            fontweight="bold", va="top", color="gray")

    plt.tight_layout()
    save_path = os.path.join(config.OUTPUT_DIR, "02_temp_heatmap.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


def plot_temp_trends(df: pd.DataFrame, font_path: Optional[str] = None) -> str:
    """图表3：代表性城市 7 日气温趋势折线图"""
    print("\n--- 生成图表3: 城市 7 日气温趋势折线图 ---")

    representative_cities = ["北京", "上海", "广州", "成都",
                             "哈尔滨", "乌鲁木齐", "拉萨", "武汉"]

    plot_df = df[df["城市"].isin(representative_cities)].copy()
    if plot_df.empty:
        print("  [!] 无代表性城市数据，跳过趋势图")
        return ""

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
        ax.fill_between(x_pos, highs, lows, alpha=0.1, color="#9B59B6")

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

    fig.suptitle("代表性城市未来 7 日气温变化趋势",
                 fontsize=18, fontweight="bold", y=1.02, fontproperties=fp)
    plt.tight_layout()
    save_path = os.path.join(config.OUTPUT_DIR, "03_temp_trends.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path


def plot_weather_pie_chart(df: pd.DataFrame, font_path: Optional[str] = None) -> str:
    """图表4：各省份主要天气类型饼图（前 8 省）"""
    print("\n--- 生成图表4: 天气状况饼图 ---")

    fp = _get_font_prop(font_path)
    top_provinces = df["省份"].value_counts().head(8).index.tolist()

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    colors = plt.cm.Set3(np.linspace(0, 1, 10))

    for i, province in enumerate(top_provinces):
        ax = axes[i]
        prov_data = df[df["省份"] == province]
        weather_dist = prov_data["天气状况"].value_counts()

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

        for t in texts:
            if fp:
                t.set_fontproperties(fp)
        for t in autotexts:
            t.set_fontsize(8)

        ax.set_title(province, fontsize=14, fontweight="bold", fontproperties=fp)

    fig.suptitle("各省份主要天气类型分布（前 8 省）",
                 fontsize=18, fontweight="bold", y=1.02, fontproperties=fp)
    plt.tight_layout()
    save_path = os.path.join(config.OUTPUT_DIR, "04_weather_pie_chart.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 已保存: {save_path}")
    return save_path
