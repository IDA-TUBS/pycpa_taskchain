#!/bin/bash
python examples/plot_scatter_path.py path_report.csv --relative --original lat1 --improved lat2
python examples/plot_scatter_path.py path_report.csv --relative --original lat1 --improved lat3
python examples/plot_scatter_path.py path_report.csv --relative --original lat2 --improved lat3
python examples/plot_scatter_wcrt.py wcrt_report.csv --xtask T1a --ytask T1b
python examples/plot_scatter_wcrt.py wcrt_report.csv --xtask T2a --ytask T2b
python examples/plot_scatter_wcrt.py wcrt_report.csv --xtask T3a --ytask T3b
python examples/plot_scatter_wcrt.py wcrt_report.csv --xtask T4a --ytask T4b
python examples/plot_scatter_wcrt.py wcrt_report.csv --xtask T5a --ytask T5b
python examples/plot_scatter_wcrt.py wcrt_report.csv --xtask T6a --ytask T6b
