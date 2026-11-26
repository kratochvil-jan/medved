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

MEDVED = "🧸"
MEDVED_BAR = MEDVED * 10

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

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
    def __init__(
        self,
        runnable: Runnable,
        reason: str,
        error_parts: list[tuple[str, str]],
    ):
        self.runnable = runnable
        self.reason = reason
        self.error_parts = error_parts

    def __str__(self) -> str:
        def fmt(text: str) -> str:
            return f"{YELLOW}{text}{RESET}"

        parts = (
            [("reason:", self.reason)]
            + self.error_parts
            + [("medved comment:", self.runnable.comment_string)]
        )

        parts = [
            "",
            f"{RED}{BOLD}{MEDVED_BAR}{RESET}",
            f"  {RED}{BOLD}MEDVED FAILED{RESET}",
            f"{RED}{BOLD}{MEDVED_BAR}{RESET}",
        ] + ["\n".join((fmt(key), value.strip(), "")) for key, value in parts]

        return "\n".join(parts)


class RunnableExecException(RunnableException):
    def __init__(self, runnable: Runnable, e: Exception, command: str, stderr: str):
        parts = [("command:", command), ("stderr:", stderr.strip())]
        super().__init__(runnable, "Python exec raised exception", parts)


class RunnableSubprocessException(RunnableException):
    def __init__(
        self,
        runnable: Runnable,
        e: subprocess.CalledProcessError,
        command: str,
        stdin: str,
        stderr: str,
    ):
        parts = [("command", command), ("stdin", stdin), ("stderr", stderr)]
        super().__init__(
            runnable,
            f"Command failed with exit code {e.returncode}",
            parts,
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
    def _wrap_eval(self, eval: str) -> str:
        return f"nix eval --impure --expr '{eval}'"

    def _run(self, process: str) -> str:
        result = subprocess.run(
            process,
            text=True,
            shell=True,
            check=False,
            capture_output=True,
        )

        print(result.stderr, file=sys.stderr, end="")

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                process,
                output=result.stdout,
                stderr=result.stderr,
            )

        return strip_quotes(result.stdout.strip()).replace("\\n", "\n")

    def nix_eval_flake(self, flake_output: str, eval: str) -> str:
        process = f"""\
nix eval --raw '{flake_output}' --apply '
flakeOutput:
    let
        inherit (flakeOutput) pkgs;
        inherit (pkgs) lib;
    {eval}
'
"""

        return self._run(process)

    def nix_eval_flake_slow(
        self, eval: str, pkgs=False, nixpkgs: str = "nixpkgs"
    ) -> str:
        """
        This imports the flake in `--impure`, so it's very slow
        """

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
        return self._run(self._wrap_eval(expr))

    def nix_eval(self, expr: str) -> str:
        process = f"""\
let
    pkgs = import <nixpkgs>{{}};
    lib = pkgs.lib;
    {expr}
"""
        return self._run(self._wrap_eval(process))

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
        except subprocess.CalledProcessError as e:
            raise RunnableExecException(
                runnable, e, e.cmd, stderr.getvalue().strip()
            ) from None

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
            runnable,
            e,
            e.cmd,
            runnable.process_stdin,
            e.stderr.strip() if e.stderr else "",
        ) from None


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

        try:
            processed = process_file(filename)
        except RunnableException as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        print(processed, end="")
        if args.replace:
            filename.write_text(processed)


if __name__ == "__main__":
    main()
