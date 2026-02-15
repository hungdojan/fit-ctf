import asyncio
import os
import tempfile
from asyncio.subprocess import Process
from subprocess import call

from termcolor import colored

from fit_ctf_components.data_parser import YamlParser
from fit_ctf_components.exceptions import ConfigurationFileNotEditedException


# NOTE: source link of the code: https://stackoverflow.com/a/6309753
def document_editor(
    doc: dict, read_only_fields: set = set(), validator_name: str | None = None
) -> dict:
    """Allows user to edit configuration files in the system editor."""
    editor = os.getenv("EDITOR")
    if not editor:
        raise ValueError("$EDITOR not set.")
    excluded_data = {k: doc.pop(k) for k in read_only_fields if k in doc}

    with tempfile.NamedTemporaryFile(suffix=".tmp.yaml", mode="w+") as tf:
        # dump the content of the data into the file
        tf.write(YamlParser.dump_data(doc))
        tf.flush()

        initial_mod_time = os.path.getmtime(tf.name)

        # call the editor for editing
        call([editor, tf.name])

        # check if the file was modified
        if not (os.path.getmtime(tf.name) > initial_mod_time):
            raise ConfigurationFileNotEditedException()

        # do the parsing with `tf` using regular File operations.
        # for instance:
        tf.seek(0)
        doc = YamlParser.load_data_stream(tf, validator_name)

    doc.update(excluded_data)
    return doc


def color_state(state: str) -> str:
    """Colors the text of the state field based on its value."""
    out = ""
    if state == "running":
        out = colored(state, "green")
    elif state in {"created", "initialized", "paused"}:
        out = colored(state, "yellow")
    else:
        out = colored(state, "red")
    return out


def get_missing_in_sequence(arr: list[int], start_val: int) -> int:
    if not arr:
        return start_val
    index = 0
    step = len(arr) // 2
    while step > 0:
        while index + step < len(arr) and arr[index + step] == start_val + index + step:
            index += step
        step //= 2

    value = arr[index]
    if index == 0 and arr[index] != start_val:
        return start_val
    return value + 1


async def create_async_exec(cmd: list[str]) -> tuple[Process, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await proc.communicate()
    return proc, stdout
