import logging
import json
import copy
from pathlib import Path

from bot import DChanBot

logger = logging.getLogger("dchanbot.config")

class Config:
    def __init__(self, confdir : Path, name : str, bot : DChanBot):
        if confdir.exists() is False:
            raise FileNotFoundError(f"Path is not found: {confdir}")
        if confdir.is_dir() is False:
            raise NotADirectoryError(f"Not a directory: {confdir}")

        self._confdir = confdir
        self._confpath = confdir / f"{name}.json"

        self._bot = bot
        self._confcache = {}    # 設定データのメモリキャッシュ

    # 設定をファイルから読み込む
    def load(self, initconf : dict = None):
        if self._confpath.exists():
            with self._confpath.open(mode="r", encoding="utf-8") as f:
                self._confcache = json.load(f)
        else:
            initconf_ = initconf or {}
            with self._confpath.open(mode="w", encoding="utf-8") as f:
                json.dump(initconf_, f, indent = 4)
            self._confcache = copy.deepcopy(initconf_)

    # 設定をファイルに保存
    def save(self):
        with self._confpath.open(mode = 'w', encoding="utf-8") as f:
            json.dump(self._confcachel, f, indent = 4)    

    # 指定された設定データの取得
    def get(self, *keys, default=None):
        data = self._confcache
        try:
            for key in keys:
                data = data[key]
            return data
        except:
            return default  # 見つからなければ規定値を返す

    # 設定データの変更
    def set(self, value, *keys):
        data = self._confcache
        for key in keys[:-1]:
            if key not in data or not isinstance(data[key], dict):
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value
