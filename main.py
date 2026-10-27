#!/usr/bin/env python3

import argparse
import io
import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path

RE_CODE_BLOCK = re.compile(r"^[ \t]*(`{3,}|~{3,})", re.MULTILINE)
RE_COMMENT = re.compile(
    r"<!-- (?P<cmd_type>\w+) (?P<out_fmt>\w+)( (?P<out_fmt_param>\w+))?\n(?P<process>.*?)\n(?P<process_stdin>.*?)-->",
    re.DOTALL,
)
MARK_END = "<!-- END -->"
RE_MARK_END = re.compile(MARK_END)


class CmdType(Enum):
    RUN = "run"


class OutFmt(Enum):
    CODE = "code"
    LIST = "list"
    TEXT = "text"


class UnknownOutFmtException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class CommentRunnableParseException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class RunnableException(Exception):
    def __init__(self, runnable: Runnable, reason: str, stderr: str):
        self.runnable = runnable
        self.reason = reason
        self.stderr = stderr

    def __str__(self) -> str:
        return f"""\
{self.reason}
Stderr: '{self.stderr}'
Text of the failing comment:
'''
{self.runnable.comment_string}
'''
"""


class RunnableExecException(RunnableException):
    def __init__(self, runnable: Runnable, e: Exception, stderr: str):
        super().__init__(runnable, f"Python exec raised exception '{e}'", stderr)


class RunnableSubprocessException(RunnableException):
    def __init__(
        self, runnable: Runnable, e: subprocess.CalledProcessError, stderr: str
    ):
        super().__init__(
            runnable,
            f"Command '{runnable.process}' failed with exit code {e.returncode}",
            stderr,
        )


@dataclass
class Runnable:
    cmd_type: CmdType
    out_fmt: OutFmt
    out_fmt_param: str
    process: str
    process_stdin: str
    comment_string: str

    @staticmethod
    def from_match(match: re.Match) -> Runnable:
        converted = match.groupdict()

        try:
            for field in fields(Runnable):
                typ = field.type
                value = converted.get(field.name)

                if isinstance(typ, type) and issubclass(typ, Enum):
                    converted[field.name] = typ(value)

            converted["comment_string"] = match.group(0)
            return Runnable(**converted)
        except Exception as e:
            raise CommentRunnableParseException(
                f"Failed to parse Runnable from string:\n'{match.group(0)}'"
            ) from e


def ensure_newline(text: str) -> str:
    return text.strip() + "\n"


def fmt(runnable: Runnable, stdout: str) -> str:
    match runnable.out_fmt:
        case OutFmt.CODE:
            return fmt_code(stdout, runnable.out_fmt_param)
        case OutFmt.LIST:
            return fmt_list(stdout)
        case OutFmt.TEXT:
            return ensure_newline(stdout)
        case _:
            raise UnknownOutFmtException(f"Unknown output format: {runnable.out_fmt}")


def fmt_code(stdout: str, param: str) -> str:
    return ensure_newline(f"```{param}\n{ensure_newline(stdout)}```")


def fmt_list(stdout: str) -> str:
    return ensure_newline(
        "\n".join([f"- {line}" for line in stdout.split("\n") if line])
    )


def strip_quotes(text: str) -> str:
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    return text


class Stdlib:
    @staticmethod
    def _nix_eval(eval: str) -> str:
        process = f"nix eval --impure --expr '{eval}'"

        result = subprocess.check_output(
            process,
            text=True,
            shell=True,
            stderr=subprocess.PIPE,
        )
        return strip_quotes(result.strip()).replace("\\n", "\n")

    def nix_eval_flake(self, eval: str, pkgs=False, nixpkgs: str = "nixpkgs") -> str:
        expr_pkgs = (
            f"pkgs = import flake.inputs.{nixpkgs} {{ inherit system; }};"
            if pkgs and nixpkgs
            else ""
        )
        expr = f"""\
let
    flake = builtins.getFlake (toString ./.);
    system = builtins.currentSystem;
    lib = flake.inputs.nixpkgs.lib;
    {expr_pkgs}
    {eval}
"""
        return Stdlib._nix_eval(expr)

    def nix_eval(self, expr: str) -> str:
        return Stdlib._nix_eval(expr)

    @staticmethod
    def as_dict():
        stdlib = Stdlib()
        return {
            name: getattr(stdlib, name)
            for name, attr in vars(Stdlib).items()
            if not name.startswith("_")
            and callable(getattr(stdlib, name))
            and not isinstance(attr, staticmethod)
        }


def run_process(runnable: Runnable) -> str | None:
    if runnable.process == "python-stdlib":
        stdlib = Stdlib.as_dict()

        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                # ruff: ignore [S102]
                exec(runnable.process_stdin, globals=stdlib)
            return stdout.getvalue().strip()
        except Exception as e:
            raise RunnableExecException(runnable, e, stderr.getvalue().strip()) from e

    try:
        result = subprocess.run(
            runnable.process,
            input=runnable.process_stdin,
            text=True,
            shell=True,
            capture_output=True,
            check=True,
        )
        return result.stdout or ""
    except subprocess.CalledProcessError as e:
        raise RunnableSubprocessException(
            runnable, e, e.stderr.strip() if e.stderr else ""
        ) from e


def process_file(file: Path) -> str:
    return process(file.read_text())


def is_inside_code_block(text: str) -> bool:
    matches = RE_CODE_BLOCK.finditer(text, 0)
    return len(list(matches)) % 2 == 1


def process(file_text: str) -> str:
    """
    - Scan the file from top to bottom
    - Repeat:
        - Search the comment string
        - Parse the comment syntax
        - Execute the commands in a process
        - Figure out where to paste the stdout:
            - If an END comment mark is found, replace everything until that mark
            - Otherwise, paste the stdout directly after
    """

    markdown = []

    offset = 0
    while True:
        match = RE_COMMENT.search(file_text, pos=offset)
        if not match:
            break

        # Include everything in OG markdown until the match, including the match
        markdown.append(file_text[offset : match.end()])

        if is_inside_code_block(file_text[: match.start()]):
            offset = match.end()
            continue

        # Parse the matched comment regex
        try:
            runnable = Runnable.from_match(match)
        except CommentRunnableParseException:
            offset = match.end()
            continue

        if runnable.cmd_type != CmdType.RUN:
            offset = match.end()
            continue

        # Run the process and format the stdout
        stdout = run_process(runnable)
        assert stdout is not None
        stdout = fmt(runnable, stdout)

        # Append the formatted stdout

        markdown.append("\n")
        markdown.append("\n")
        markdown.append(stdout)
        markdown.append("\n")
        markdown.append(MARK_END)

        # Figure out where to jump the offset head

        next_match = RE_COMMENT.search(file_text, pos=match.end())
        marker_end = RE_MARK_END.search(
            file_text,
            pos=match.end(),
            endpos=next_match.start() if next_match else sys.maxsize,
        )

        if marker_end:
            # End marker found - jump after it
            offset = marker_end.end()
        else:
            # Jump to the next comment
            offset = match.end()

    # Reading comments is finished.
    # Include the rest of the document
    markdown.append(file_text[offset:])

    return "".join(markdown)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace contents of the files",
    )
    parser.add_argument("filenames", nargs="+", type=Path, help="Input files")

    args = parser.parse_args()

    for filename in args.filenames:
        assert isinstance(filename, Path)

        processed = process_file(filename)
        print(processed, end="")
        if args.replace:
            filename.write_text(processed)


if __name__ == "__main__":
    main()
