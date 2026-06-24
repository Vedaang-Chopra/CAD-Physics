# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/evaluation/python_kernel.py
import os
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple

class PythonKernel:
    """
    A utility class to execute Python code in an isolated manner.
    Can be used independently in Jupyter Notebooks to test generated Code.
    """
    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def run_code(self, code: str, working_dir: Path = None, filename: str = "temp_execution.py") -> Tuple[bool, str, str]:
        """
        Executes the provided python code via subprocess in the given working directory.
        If working_dir is None, creates a temporary directory.
        Returns (success: bool, stdout: str, stderr: str)
        """
        if working_dir is None:
            # When working_dir is none, run inside a temporary directory and return results.
            with tempfile.TemporaryDirectory() as tmpdirname:
                return self._execute_in_dir(code, Path(tmpdirname), filename)
        else:
            return self._execute_in_dir(code, working_dir, filename)

    def _execute_in_dir(self, code: str, current_dir: Path, filename: str) -> Tuple[bool, str, str]:
        script_path = current_dir / filename
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        try:
            print(f"Executing {filename} in {current_dir.name}...")
            start_time = time.time()
            result = subprocess.run(
                ["python3", filename],
                cwd=current_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                print(f"Execution successful (t={elapsed:.1f}s).")
                return True, result.stdout, result.stderr
            else:
                print(f"Execution failed (t={elapsed:.1f}s):\n{result.stderr[:200]}...")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            print("Execution timed out.")
            return False, "", "Timeout"
        except Exception as e:
            print(f"Execution error: {e}")
            return False, "", str(e)
