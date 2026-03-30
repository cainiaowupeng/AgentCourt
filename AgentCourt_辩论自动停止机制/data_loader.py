import pandas as pd
import json


def read_file(path):
    if path.endswith('csv'):
        return pd.read_csv(path)
    elif path.endswith('xlsx'):
        return pd.read_excel(path)
    elif path.endswith('json'):
        with open(path, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    elif path.endswith('txt'):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError('Unexpected file type!')


def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1))


def load(path):
    reqs = read_file(path)
    return reqs


def output(path, data):
    write_json(path, data)

