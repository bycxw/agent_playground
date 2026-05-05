"""
Phase 2: Qlib research pipeline
  Data      → Alpha158 technical factors on CSI300
  Model     → LightGBM (5-day forward return prediction)
  Backtest  → TopkDropoutStrategy, real trading costs, T+1 open price
  Output    → signals/daily.parquet  (date, instrument, score)
"""
from pathlib import Path
import pandas as pd
import qlib
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.evaluate import backtest_daily, risk_analysis
from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR   = Path("~/.qlib/qlib_data/cn_data").expanduser()
OUTPUT_DIR = Path(__file__).parent / "signals"
OUTPUT_DIR.mkdir(exist_ok=True)

UNIVERSE   = "csi300"

TRAIN_START = "2008-01-01"
TRAIN_END   = "2017-12-31"
VALID_START = "2018-01-01"
VALID_END   = "2019-12-31"
TEST_START  = "2020-01-01"
TEST_END    = "2021-06-10"   # data ends 2021-06-11

TOPK   = 30   # stocks to hold at any time
N_DROP = 5    # stocks replaced per rebalance

EXCHANGE_KWARGS = {
    "open_cost":       0.0003,
    "close_cost":      0.0013,   # commission + stamp duty
    "limit_threshold": 0.095,    # ±9.5% price limit filter
    "deal_price":      "open",   # T+1: execute at next day's open
}


# ── Step 1: Init ──────────────────────────────────────────────────────────────

def init():
    print("=== Step 1: Init Qlib ===")
    qlib.init(provider_uri=str(DATA_DIR), region=REG_CN)
    print(f"Data: {DATA_DIR}\n")


# ── Step 2: Build dataset ─────────────────────────────────────────────────────

def build_dataset():
    print("=== Step 2: Build dataset (Alpha158) ===")

    handler = Alpha158(
        instruments=UNIVERSE,
        start_time=TRAIN_START,
        end_time=TEST_END,
        fit_start_time=TRAIN_START,
        fit_end_time=TRAIN_END,
    )

    dataset = DatasetH(
        handler=handler,
        segments={
            "train": (TRAIN_START, TRAIN_END),
            "valid": (VALID_START, VALID_END),
            "test":  (TEST_START,  TEST_END),
        },
    )

    train_df = dataset.prepare("train")
    print(f"Train shape:  {train_df.shape}")
    print(f"Features:     {[c for c in train_df.columns if c != 'label'][:5]} ... "
          f"({train_df.shape[1] - 1} total)")
    print(f"Label column: label\n")

    return dataset


# ── Step 3: Train model ───────────────────────────────────────────────────────

def train_model(dataset):
    print("=== Step 3: Train LightGBM ===")

    model = LGBModel(
        loss="mse",
        learning_rate=0.05,
        num_leaves=128,
        num_boost_round=200,
        colsample_bytree=0.8,
        subsample=0.8,
        lambda_l1=0.1,
        lambda_l2=0.1,
        verbose=-1,
    )

    model.fit(dataset)
    print("Training done\n")
    return model


# ── Step 4: Evaluate predictions ──────────────────────────────────────────────

def evaluate(model, dataset):
    print("=== Step 4: Evaluate (IC / ICIR) ===")

    pred = model.predict(dataset, segment="test")
    label = dataset.prepare("test", col_set="label").iloc[:, 0]

    # Align index
    common = pred.index.intersection(label.index)
    pred_aligned  = pred.loc[common]
    label_aligned = label.loc[common]

    # IC: per-day cross-sectional correlation between pred and realized return
    df = pd.concat([pred_aligned.rename("pred"), label_aligned.rename("label")], axis=1)
    ic_vals = {
        dt: float(grp["pred"].corr(grp["label"]))
        for dt, grp in df.groupby(level="datetime")
    }
    ic_series = pd.Series(ic_vals)

    ic   = float(ic_series.mean())
    icir = float(ic_series.mean() / ic_series.std())

    print(f"Test IC:   {ic:.4f}   (target > 0.05)")
    print(f"Test ICIR: {icir:.4f}  (target > 0.5)")
    print(f"IC > 0:    {(ic_series > 0).mean():.1%} of days\n")

    return pred


# ── Step 5: Backtest ──────────────────────────────────────────────────────────

def run_backtest(model, dataset):
    print("=== Step 5: Backtest ===")

    strategy = TopkDropoutStrategy(
        signal=(model, dataset),
        topk=TOPK,
        n_drop=N_DROP,
    )

    portfolio_metrics, indicator = backtest_daily(
        start_time=TEST_START,
        end_time=TEST_END,
        strategy=strategy,
        exchange_kwargs=EXCHANGE_KWARGS,
        benchmark="SH000300",
    )

    analysis = risk_analysis(portfolio_metrics["return"] - portfolio_metrics["bench"])
    print(portfolio_metrics.describe())
    print("\nExcess return analysis:")
    print(analysis)
    print()

    return portfolio_metrics


# ── Step 6: Save signals ──────────────────────────────────────────────────────

def save_signals(pred: pd.Series):
    print("=== Step 6: Save signals ===")

    df = (
        pred
        .rename("score")
        .reset_index()
        .rename(columns={"datetime": "date", "instrument": "symbol"})
        .sort_values(["date", "score"], ascending=[True, False])
    )

    # Daily rank (1 = highest predicted return)
    df["rank"] = df.groupby("date")["score"].rank(ascending=False, method="first").astype(int)

    out = OUTPUT_DIR / "daily.parquet"
    df.to_parquet(out, index=False)
    print(f"Signals saved: {out}")
    print(f"Shape: {df.shape}")
    print(df[df["rank"] <= 3].head(9).to_string(index=False))
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init()
    dataset = build_dataset()
    model   = train_model(dataset)
    pred    = evaluate(model, dataset)
    run_backtest(model, dataset)
    save_signals(pred)
    print("=== Pipeline complete ===")
