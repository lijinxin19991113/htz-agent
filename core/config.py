"""
配置加载模块
"""
import os
import yaml
from pathlib import Path


class Config:
    """配置管理类"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self.load()

    def load(self, config_path: str = None):
        """加载配置文件"""
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        # 替换环境变量
        self._replace_env_vars(self._config)

    def _replace_env_vars(self, obj):
        """递归替换环境变量占位符 ${VAR_NAME}"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    obj[k] = os.environ.get(env_var, "")
                else:
                    self._replace_env_vars(v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    obj[i] = os.environ.get(env_var, "")
                else:
                    self._replace_env_vars(v)

    def get(self, key: str, default=None):
        """获取配置项，支持点号分隔的路径，如 'game.platform'"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def game(self):
        return self._config.get("game", {})

    @property
    def api(self):
        return self._config.get("api", {})

    @property
    def delay(self):
        return self._config.get("delay", {})

    @property
    def resolution(self):
        return self._config.get("resolution", {})


if __name__ == "__main__":
    cfg = Config()
    print(f"Platform: {cfg.get('game.platform')}")
    print(f"ADB Serial: {cfg.get('game.adb_serial')}")
