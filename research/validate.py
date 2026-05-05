"""
Phase 0 validation: Qlib + A-share data pipeline.
Steps:
  1. Download pre-packaged cn data (qlib_data_simple, ~small size)
  2. Initialize Qlib
  3. Query basic price factors for a few stocks
  4. Compute a simple Alpha factor (5-day return momentum)
"""
import sys
from pathlib import Path

DATA_DIR = Path("~/.qlib/qlib_data/cn_data").expanduser()


def step1_download():
    print("=== Step 1: Download cn data ===")
    from qlib.tests.data import GetData
    GetData().qlib_data(
        name="qlib_data_simple",
        target_dir=str(DATA_DIR),
        region="cn",
        interval="1d",
        exists_skip=True,  # skip if already downloaded
    )
    print(f"Data at: {DATA_DIR}\n")


def step2_init():
    print("=== Step 2: Initialize Qlib ===")
    import qlib
    qlib.init(provider_uri=str(DATA_DIR), region="cn")
    print("Qlib initialized\n")


def step3_query_price():
    print("=== Step 3: Query price data ===")
    from qlib.data import D

    # Query close price for 3 stocks, last 10 trading days
    stocks = ["sh600000", "sz000001", "sh600519"]
    df = D.features(
        instruments=stocks,
        fields=["$close", "$volume", "$open"],
        start_time="2020-01-01",
        end_time="2020-01-31",
        freq="day",
    )
    print(df.head(15))
    print(f"\nShape: {df.shape}\n")


def step4_alpha_factor():
    print("=== Step 4: Compute simple momentum factor ===")
    from qlib.data import D

    # 5-day momentum: close / Ref(close, 5) - 1
    df = D.features(
        instruments=["sh600000", "sz000001", "sh600519"],
        fields=["$close/Ref($close,5)-1"],
        start_time="2020-01-01",
        end_time="2020-03-31",
        freq="day",
    )
    df.columns = ["mom_5d"]
    print(df.head(15))
    print(f"\nMomentum factor stats:\n{df['mom_5d'].describe()}\n")
    print("=== All steps passed. Qlib is working correctly. ===")


if __name__ == "__main__":
    step1_download()
    step2_init()
    step3_query_price()
    step4_alpha_factor()
