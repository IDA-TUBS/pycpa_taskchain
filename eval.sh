#!/bin/bash
python examples/plot_scatter_path.py path_report.csv --relative --original lat --improved lat_sync
python examples/plot_scatter_path.py path_report.csv --relative --original lat --improved lat_async
python examples/plot_scatter_path.py path_report.csv --relative --original lat_sync --improved lat_syncref
