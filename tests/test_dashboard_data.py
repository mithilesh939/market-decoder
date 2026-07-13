import tempfile
import unittest
from pathlib import Path

from dashboard.app import build_dashboard_layout, load_monthly_dataset, prepare_market_frame


class DashboardDataTests(unittest.TestCase):
    def test_load_monthly_dataset_reads_all_csvs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "2025-01.csv").write_text(
                "timestamp,price,volume\n2025-01-01T00:00:00,100,10\n",
                encoding="utf-8",
            )
            (data_dir / "2025-02.csv").write_text(
                "timestamp,price,volume\n2025-02-01T00:00:00,110,12\n",
                encoding="utf-8",
            )

            monthly_df, csv_files = load_monthly_dataset(data_dir)

            self.assertEqual(len(csv_files), 2)
            self.assertEqual(monthly_df["month"].nunique(), 2)
            self.assertEqual(monthly_df.loc[monthly_df["month"] == "2025-01", "records"].iloc[0], 1)
            self.assertEqual(monthly_df.loc[monthly_df["month"] == "2025-02", "records"].iloc[0], 1)

    def test_prepare_market_frame_derives_rich_market_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "2025-01.csv").write_text(
                "timestamp,price,volume\n2025-01-01T00:00:00,100,10\n2025-01-02T00:00:00,110,20\n",
                encoding="utf-8",
            )

            frame = prepare_market_frame(data_dir)

            self.assertGreaterEqual(len(frame), 2)
            self.assertIn("returns", frame.columns)
            self.assertIn("moving_average", frame.columns)
            self.assertIn("rolling_volatility", frame.columns)
            self.assertIn("cumulative_return", frame.columns)
            self.assertIn("inventory", frame.columns)
            self.assertIn("realized_pnl", frame.columns)

    def test_build_dashboard_layout_includes_engineering_and_simulation_copy(self):
        layout = build_dashboard_layout()
        rendered = str(layout)

        self.assertIn("Pipeline", rendered)
        self.assertIn("Strategy Simulation", rendered)
        self.assertIn("Dataset Summary", rendered)


if __name__ == "__main__":
    unittest.main()
