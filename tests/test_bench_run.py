import unittest

from atex.bench.run import BenchResult, format_results_md


class TestFormatResultsMarkdown(unittest.TestCase):
    def test_empty_results_contains_only_markdown_header(self):
        self.assertEqual(
            format_results_md([]),
            "| backend | ingest_n | ingest_ms | throughput (entries/s) | recall@1 | recall@3 | recall@5 | avg query (ms) | p99 (ms) | cold-start (ms) |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        )

    def test_formats_zero_and_fractional_metrics_with_documented_precision(self):
        result = BenchResult(
            name="boundary",
            ingest_n=0,
            ingest_wall_s=0.00004,
            ingest_throughput_entries_per_s=0.5,
            recall_at_1=0.005,
            recall_at_3=0.995,
            recall_at_5=1.0,
            avg_query_ms=0.0,
            p99_query_ms=1.25,
            cold_start_ms=0.0,
        )

        self.assertEqual(
            format_results_md([result]),
            "| backend | ingest_n | ingest_ms | throughput (entries/s) | recall@1 | recall@3 | recall@5 | avg query (ms) | p99 (ms) | cold-start (ms) |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
            "| boundary | 0 | 0.0 | 0 | 0% | 100% | 100% | 0.0 | 1.25 | 0.0 |",
        )

    def test_rejects_non_result_rows(self):
        with self.assertRaises(AttributeError):
            format_results_md([object()])


if __name__ == "__main__":
    unittest.main(verbosity=2)
