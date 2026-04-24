import asyncio
import os
import pathlib
import tempfile
from asyncio.subprocess import Process
from subprocess import call

from termcolor import colored

from fit_ctf.components.data_parser import YamlParser
from fit_ctf.components.exceptions import ConfigurationFileNotEditedException


# NOTE: source link of the code: https://stackoverflow.com/a/6309753
def yaml_doc_editor(
    doc: dict, read_only_fields: set = set(), validator_name: str | None = None
) -> dict:
    """Allows user to edit configuration files in the system editor."""
    editor = os.getenv("EDITOR")
    if not editor:
        raise ValueError("$EDITOR not set.")
    excluded_data = {k: doc.pop(k) for k in read_only_fields if k in doc}

    with tempfile.NamedTemporaryFile(suffix=".tmp.yaml", mode="w+", delete=False) as tf:
        # dump the content of the data into the file
        tf.write(YamlParser.dump_data(doc))
        tf.flush()
        temp_path = tf.name

    try:
        initial_mod_time = os.path.getmtime(temp_path)

        # call the editor for editing
        call([editor, temp_path])

        # check if the file was modified
        if not (os.path.getmtime(temp_path) > initial_mod_time):
            raise ConfigurationFileNotEditedException("Document not changed")

        # Re-open and read the edited file from disk
        with open(temp_path, "r") as edited_file:
            new_doc = YamlParser.load_data_stream(edited_file, validator_name)
    finally:
        # Clean up temp file
        os.unlink(temp_path)

    # Merge back read-only fields and return the edited document
    new_doc.update(excluded_data)
    return new_doc


def file_editor(dest_file: pathlib.Path):
    """Open a file in $EDITOR and save changes in-place."""
    editor = os.getenv("EDITOR")
    if not editor:
        raise ValueError("$EDITOR not set.")

    if not os.path.exists(dest_file):
        # optionally create empty file
        open(dest_file, "w").close()

    initial_mod_time = os.path.getmtime(dest_file)

    call([editor, dest_file])

    # detect if user actually changed something
    if os.path.getmtime(dest_file) <= initial_mod_time:
        print("File was not modified.")
    else:
        print("File updated.")


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
