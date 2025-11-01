import os


def read_instructions_from_file(file_path: str) -> str:
    with open(file_path, 'r') as f:
        return f.read()