import shlex
import subprocess

from fastapi import HTTPException

ALLOWED_DF_ARGS = {"-h", "-H", "-T", "-i", "-a", "-l", "-P", "-k"}


def get_disk_usage(parameters: str):
    args = shlex.split(parameters) if parameters else []

    for arg in args:
        if arg not in ALLOWED_DF_ARGS:
            raise HTTPException(
                status_code=400, detail=f"Parameter not allowed: {arg}"
            )

    command = ["df", "-h", *args]

    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
        )
        usage = result.stdout.strip().decode()
    except Exception:
        raise Exception("An unexpected error was observed")

    return usage
