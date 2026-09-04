"""CLI wrapper for the learned alert-priority model.

Usage:
  python -m aura_mas.scripts.train_alert_priority "results/run_*.json"
"""
from aura_mas.alert_priority import main


if __name__ == "__main__":
    main()
