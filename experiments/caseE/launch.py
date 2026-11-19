import subprocess, sys
from concurrent.futures import ThreadPoolExecutor
jobs = [("kb","1"),("cite","1"),("light","1"),("none","1"),("note","1"),("cite","2"),("light","2"),("none","2"),("note","2"),("cite","3"),("light","3"),("none","3")]
def go(j):
    with open(f"launch_{j[0]}{j[1]}.log","w") as f:
        subprocess.run(["uv","run","python","run_e.py","all",*j], stdout=f, stderr=subprocess.STDOUT)
    print("done", *j, flush=True)
with ThreadPoolExecutor(5) as ex:
    list(ex.map(go, jobs))
