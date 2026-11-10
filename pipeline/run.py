"""Orchestrator and CLI entry point:  python -m pipeline.run

To write (plan section 6, run.py):
- main() -> int: set up logging, read settings, create the engine
- insert a 'running' row into pipeline_runs and keep its run_id
- extract (api or csv) -> transform -> validate -> load, inside try/except
- always update the pipeline_runs row: finished_at, status, row counts, error
- return 0 on success, 1 on failure (non-zero exit = red X in Actions)
- if __name__ == "__main__": sys.exit(main())
"""
