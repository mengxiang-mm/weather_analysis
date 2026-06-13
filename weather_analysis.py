#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
┌────────────────────────────────────────────────────────────┐
│  天气数据分析系统  v2.0                                    │
│                                                           │
│  架构: 模块化拆分，数据与配置统一由 province_data.json 管理  │
│                                                           │
│  使用:                                                     │
│    python weather_analysis.py              # 爬虫模式      │
│    python weather_analysis.py --sample     # 样本模式      │
│    python weather_analysis.py --output ./data  # 自定义输出 │
└────────────────────────────────────────────────────────────┘
"""

import sys
import os

# 确保包目录在路径中
PKG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_analysis_pkg")
if PKG_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(PKG_DIR))

from weather_analysis_pkg.cli import main

if __name__ == "__main__":
    main()
