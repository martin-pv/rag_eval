from pathlib import Path
from os import environ
from types import SimpleNamespace, GeneratorType
import json


def set_prox():
    """Run this if you are seeing proxy errors in your console."""
    if ".azure.us" not in environ["no_proxy"]:
        environ["no_proxy"] += ",.azure.us"
    if ".rtx.com" not in environ["no_proxy"]:
        environ["no_proxy"] += ",.rtx.com"
    environ["http_proxy"] = ""
    environ["https_proxy"] = ""


def read_jsonl(file_name: Path = Path("data", "judge_config.jsonl")):
    """Reads and yields a SimpleNamespace object for each JSONL entry."""
    if not file_name.suffix.endswith("jsonl"):
        raise RuntimeError("read_jsonl only works with `jsonl` files.")
    with open(file_name, "r") as file:
        for line in file:
            if line.strip():
                yield json.loads(line, object_hook=lambda d: SimpleNamespace(**d))


CONFIG_DIR = Path("config")
CONFIG_REG = "*_config.json"

SETTING = {}

file_list = CONFIG_DIR.glob(CONFIG_REG)

# Load config files.
for file_name in file_list:
    with open(file_name, "r") as file:
        SETTING[file_name.stem] = json.load(file)

SETTING = SimpleNamespace(**SETTING)


if __name__ == "__main__":
    print(SETTING)
