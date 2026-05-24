try:
    from data_pipeline.pipeline import run_data_pipeline
except ImportError:  # pragma: no cover
    from pipeline import run_data_pipeline


def run_pipeline(pages_to_fetch: int = 5, embed: bool = True):
    print("Starting data pipeline")
    updated_count = run_data_pipeline(pages_to_fetch=pages_to_fetch, embed=embed)
    print(f"Finished data pipeline. Upserted {updated_count} courses")


if __name__ == "__main__":
    run_pipeline()
