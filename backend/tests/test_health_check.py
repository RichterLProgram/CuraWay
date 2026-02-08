import os
import subprocess
import sys


def test_health_check_script_runs():
    script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "health_check.py")
    )
    env = dict(os.environ)
    env["LLM_DISABLED"] = "true"
    subprocess.run([sys.executable, script], env=env, check=True)
