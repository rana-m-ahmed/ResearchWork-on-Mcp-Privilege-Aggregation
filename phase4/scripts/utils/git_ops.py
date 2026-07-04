"""
Module: git_ops.py
Purpose: Reusable Git repository inspection functions.
"""
import os
import subprocess
from typing import Dict, Optional
import logging

def get_git_state() -> Dict[str, Optional[str]]:
    """Inspects the local git repository state and returns a dictionary of information."""
    state = {
        "is_git_repo": False,
        "branch": None,
        "commit": None,
        "clean": False,
        "error": None
    }
    
    if not os.path.exists(".git"):
        state["error"] = "Not a git repository (no .git directory)"
        return state
        
    state["is_git_repo"] = True
    
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.STDOUT).decode("utf-8").strip()
        state["branch"] = branch
        
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT).decode("utf-8").strip()
        state["commit"] = commit
        
        status = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.STDOUT).decode("utf-8").strip()
        state["clean"] = len(status) == 0
        
    except subprocess.CalledProcessError as e:
        state["error"] = f"Git command failed: {e.output.decode('utf-8').strip()}"
    except Exception as e:
        state["error"] = str(e)
        
    return state
