from pathlib import Path

def repository_root():
    return Path(__file__).resolve().parents[1]

def data_dir():
    return repository_root()/'data'

def figures_dir():
    return repository_root()/'figures'

def report_dir():
    return repository_root()/'report'
