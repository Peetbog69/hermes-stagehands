"""Regressions for catalog review: clean import and profile isolation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HERMES_ROOT = Path('/usr/local/lib/hermes-agent')
for path in (ROOT, HERMES_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class ReviewRegressions(unittest.TestCase):
    def test_plugin_loads_without_pyyaml(self):
        # Run a fresh interpreter, rejecting all PyYAML imports even if installed.
        script = '''
import builtins, importlib.util, sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
real_import = builtins.__import__
def block_yaml(name, *args, **kwargs):
    if name == "yaml" or name.startswith("yaml."):
        raise ModuleNotFoundError("No module named yaml")
    return real_import(name, *args, **kwargs)
builtins.__import__ = block_yaml
spec = importlib.util.spec_from_file_location("stagehands_init", sys.argv[1] + "/__init__.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from pathlib import Path
from tempfile import TemporaryDirectory
with TemporaryDirectory() as td:
    cfg = Path(td) / "config.yaml"
    mod._write_raw_config(cfg, {"compression": {"protect_last_n": 20}}, explicit_path=True)
    _, data = mod._read_raw_config(cfg)
    assert data["compression"]["protect_last_n"] == 20
print("plugin loaded and config round-tripped")
'''
        run = subprocess.run([sys.executable, '-c', script, str(ROOT), str(HERMES_ROOT)],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('plugin loaded', run.stdout)

    def test_context_local_home_wins_over_poisoned_environment(self):
        import hermes_constants
        import stats

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            local_home = root / 'local'
            local_home.mkdir()
            local_db = local_home / 'state.db'
            local_db.touch()
            wrong_home = root / 'wrong'
            wrong_home.mkdir()
            wrong_db = wrong_home / 'state.db'
            wrong_db.touch()
            with patch.dict(os.environ, {'HERMES_HOME': str(wrong_home),
                                         'HERMES_STATE_DB': str(wrong_db),
                                         'HERMES_PROFILE': 'another'}):
                token = hermes_constants.set_hermes_home_override(local_home)
                try:
                    self.assertEqual(stats.resolve_state_db(), local_db)
                    local_db.unlink()
                    self.assertIsNone(stats.resolve_state_db())
                    self.assertEqual(stats.resolve_state_db(wrong_db), wrong_db)
                    self.assertIsNone(stats.resolve_state_db(root / 'missing'))
                finally:
                    hermes_constants.reset_hermes_home_override(token)
