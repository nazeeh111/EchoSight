"""Trusted fixed entry. No module/script path is supplied by input data."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from echosight.nlos import worker_main
if __name__=='__main__':raise SystemExit(worker_main())
