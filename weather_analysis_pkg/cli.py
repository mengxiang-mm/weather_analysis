"""
┌────────────────────────────────────────────────────────────┐
│  命令行入口 — 主流程编排                                   │
│  爬取 → 存储 → 清洗 → 分析 → 可视化                       │
└────────────────────────────────────────────────────────────┘
"""

import os
import sys
import argparse
from datetime import datetime

from . import config
from .scraper import scrape_all_weather, generate_sample_data
from .cleaner import clean_weather_data, save_to_csv
from .analyzer import analyze_by_province, analyze_weather_distribution
from .visualizer import (
    setup_chinese_font,
    plot_temp_comparison,
    plot_temperature_heatmap,
    plot_temp_trends,
    plot_weather_pie_chart,
)


def run_pipeline(use_sample: bool = False) -> None:
    """
    主流程：爬取 → 存储 → 清洗 → 分析 → 可视化
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    start_time = datetime.now()

    print(f"\n{'=' * 60}")
    print(f"  天气数据分析系统")
    print(f"  启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    # ── 阶段一：数据获取 ──
    print("\n" + "-" * 30)
    print("  阶段一：数据获取")
    print("-" * 30)

    if not use_sample:
        df_raw = scrape_all_weather()
        if df_raw.empty:
            print("\n[!] 错误：爬虫未获取到任何数据，请检查网络连接。")
            print("    可使用 --sample 参数运行示例模式。")
            sys.exit(1)
        print("\n[[OK]] 成功从墨迹天气获取数据！")
    else:
        print("[*] 使用样本数据模式。")
        df_raw = generate_sample_data()

    # ── 阶段二：数据存储 ──
    print("\n" + "-" * 30)
    print("  阶段二：数据存储")
    print("-" * 30)
    csv_path = os.path.join(config.OUTPUT_DIR, "weather_data.csv")
    save_to_csv(df_raw, csv_path)

    # ── 阶段三：数据清洗 ──
    print("\n" + "-" * 30)
    print("  阶段三：数据清洗与整理")
    print("-" * 30)
    df_clean = clean_weather_data(df_raw)
    clean_csv_path = os.path.join(config.OUTPUT_DIR, "weather_data_clean.csv")
    save_to_csv(df_clean, clean_csv_path)

    # ── 阶段四：数据分析 ──
    print("\n" + "-" * 30)
    print("  阶段四：数据分析")
    print("-" * 30)
    summary = analyze_by_province(df_clean)
    analyze_weather_distribution(df_clean)

    # ── 阶段五：数据可视化 ──
    print("\n" + "-" * 30)
    print("  阶段五：数据可视化")
    print("-" * 30)
    font_path = setup_chinese_font()

    plot_temp_comparison(summary, font_path)
    plot_temperature_heatmap(df_clean, font_path)
    plot_temp_trends(df_clean, font_path)
    plot_weather_pie_chart(df_clean, font_path)

    # ── 完成 ──
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 60)
    print(f"  [完成] 全流程完成！耗时: {elapsed:.1f} 秒")
    print("=" * 60)
    print(f"\n输出目录: {os.path.abspath(config.OUTPUT_DIR)}")
    print("  CSV 数据: weather_data.csv / weather_data_clean.csv")
    print("  统计汇总: province_temp_summary.csv")
    print("  可视化图表:")
    for name in [
        "01_avg_temp_comparison.png  — 各省平均气温对比条形图",
        "02_temp_heatmap.png         — 全国气温热力地图",
        "03_temp_trends.png          — 城市 7 日气温趋势折线图",
        "04_weather_pie_chart.png    — 天气状况饼图",
    ]:
        print(f"    {name}")

    print(f"\n输出文件大小:")
    for f in os.listdir(config.OUTPUT_DIR):
        fpath = os.path.join(config.OUTPUT_DIR, f)
        if os.path.isfile(fpath):
            print(f"  {f}: {os.path.getsize(fpath) / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="天气数据分析系统 — 爬虫 + 分析 + 可视化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python weather_analysis.py              # 正常模式（爬虫 → 分析）\n"
            "  python weather_analysis.py --sample     # 使用样本数据（跳过爬虫）\n"
        ),
    )
    parser.add_argument("--sample", action="store_true",
                        help="使用样本数据模式（跳过爬虫）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出目录（默认: ./weather_output）")

    args = parser.parse_args()

    if args.output:
        config.OUTPUT_DIR = os.path.abspath(args.output)

    banner = """
+==========================================+
|        [天气] 天气数据分析系统  v2.0       |
|                                          |
|  爬取源: 墨迹天气 (tianqi.moji.com)      |
|  功能: 爬取 -> 存储 -> 清洗 -> 分析 -> 图表 |
+==========================================+
    """
    safe_banner = banner.encode(
        sys.stdout.encoding or "utf-8", errors="replace"
    ).decode(sys.stdout.encoding or "utf-8")
    print(safe_banner)

    run_pipeline(use_sample=args.sample)
