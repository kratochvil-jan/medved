#!/usr/bin/env python3

import sys

import pytest

from main import *


# Helper to retrieve immediate match
def search_comment(text: str) -> Runnable:
    match = RE_COMMENT.search(text)
    assert match
    return Runnable.from_match(match)


def test_is_inside_code_block():
    assert True == is_inside_code_block("```\n")
    assert True == is_inside_code_block("                 ```\n")
    assert False == is_inside_code_block("```\ncontents\n```\nhello")
    assert False == is_inside_code_block("         ```\ncontents\n        ```\nhello")


def test_re_comment_wrong():
    assert None == RE_COMMENT.search("<!-- wrong format -->")


def test_re_comment_code():
    example = search_comment(
        """\
<!-- run code text
python
print("Hello")
print("World")
-->
"""
    )
    assert CmdType.RUN == example.cmd_type
    assert OutFmt.CODE == example.out_fmt
    assert "text" == example.out_fmt_param
    assert "python" == example.process
    assert 'print("Hello")\nprint("World")\n' == example.process_stdin


def test_re_comment_list():
    example = search_comment(
        """\
<!-- run list
python
print("Hello")
print("World")
-->
"""
    )
    assert CmdType.RUN == example.cmd_type
    assert OutFmt.LIST == example.out_fmt
    assert None == example.out_fmt_param
    assert "python" == example.process
    assert 'print("Hello")\nprint("World")\n' == example.process_stdin


def test_re_comment_list2():
    example = search_comment(
        """\
<!-- run list
process with some args
process stdin
-->
"""
    )
    assert CmdType.RUN == example.cmd_type
    assert OutFmt.LIST == example.out_fmt
    assert None == example.out_fmt_param
    assert "process with some args" == example.process
    assert "process stdin\n" == example.process_stdin


def test_re_comment_text():
    example = search_comment(
        """\
<!-- run text
bash
echo "- hello"
-->
"""
    )

    assert CmdType.RUN == example.cmd_type
    assert OutFmt.TEXT == example.out_fmt
    assert None == example.out_fmt_param
    assert "bash" == example.process
    assert 'echo "- hello"\n' == example.process_stdin


def test_re_comment_with_end():
    example = search_comment(
        """\
# H1
Some text here

<!-- run code text
python
print("Hello")
print("World")
-->

```text
Hello
World
```
<!-- END -->
"""
    )
    assert CmdType.RUN == example.cmd_type
    assert OutFmt.CODE == example.out_fmt
    assert "text" == example.out_fmt_param
    assert "python" == example.process
    assert 'print("Hello")\nprint("World")\n' == example.process_stdin


def test_re_comment_multi():
    example = search_comment(
        """\
# H1
Some text here

## Run 1

<!-- run code text
python
print("Hello")
print("World")
-->

```text
Hello
World
```
<!-- END -->

## Run 2

<!-- run list
python
print("Hello")
print("World")
-->
"""
    )
    # Only the first comment should be matched
    assert CmdType.RUN == example.cmd_type
    assert OutFmt.CODE == example.out_fmt
    assert "text" == example.out_fmt_param
    assert "python" == example.process
    assert 'print("Hello")\nprint("World")\n' == example.process_stdin


def test_re_mark_end_wrong_format():
    assert None == RE_MARK_END.search("<!-- wrong format -->")

    match = RE_MARK_END.search(f"Some text\n{MARK_END}\nMore text")
    assert match
    assert 10 == match.start()


def test_re_mark_end_ok():
    match = RE_MARK_END.search(
        """\
# H1
Some text here

<!-- run code text
python
print("Hello")
print("World")
-->

```text
Hello
World
```
<!-- END -->
"""
    )

    assert match
    assert 106 == match.start()
    assert 118 == match.end()


def test_ensure_newline():
    assert "\n" == ensure_newline("")[-1]
    assert "\n" == ensure_newline("hello")[-1]
    assert "\n" == ensure_newline("hello\n")[-1]


def test_fmt():
    runnable = Runnable(
        CmdType.RUN, OutFmt.CODE, "python", "whatever", "whatever", "whatever"
    )

    assert """\
```python
text out
```
""" == fmt(runnable, "text out\n")

    runnable = Runnable(
        CmdType.RUN, OutFmt.LIST, "", "whatever", "whatever", "whatever"
    )

    assert """\
- line1
- line2
""" == fmt(runnable, "line1\nline2\n")

    # No formatting applied
    runnable = Runnable(
        CmdType.RUN, OutFmt.TEXT, "", "whatever", "whatever", "whatever"
    )

    assert """\
line1
line2
""" == fmt(runnable, "line1\nline2\n")


def test_fmt_code():
    assert """\
```python
text out
```
""" == fmt_code("text out\n", "python")


def test_fmt_list():
    assert """\
- line1
- line2
""" == fmt_list("line1\nline2\n")


def test_from_match():
    # Feed a valid Match but without the proper named groups
    # -> parsing of Runnable fails
    match = re.compile("\\w").search("word")
    assert match
    with pytest.raises(CommentRunnableParseException):
        Runnable.from_match(match)


def test_strip_quotes():
    assert "string" == strip_quotes('"string"')
    assert '"string' == strip_quotes('"string')
    assert "" == strip_quotes("")


def test_process_err():
    with pytest.raises(RunnableSubprocessException):
        process(
            """\
<!-- run code shell
bash
exit 1
-->
"""
        )


def test_process_ignored_code_block():
    result = process(
        """\
```markdown
<!-- run code shell
this text is ignored because its in a code block
-->
```

<!-- run code shell
bash
echo hello
-->
"""
    )

    assert (
        """\
```markdown
<!-- run code shell
this text is ignored because its in a code block
-->
```

<!-- run code shell
bash
echo hello
-->

```shell
hello
```

<!-- END -->
"""
        == result
    )


def test_python_stdlib_nix_eval():
    runnable = search_comment(
        """\
<!-- run code nix
python-stdlib
print(nix_eval("1+1"))
-->
"""
    )

    assert "2" == run_process(runnable)


def test_python_stdlib_nix_eval_flake():
    runnable = search_comment(
        """\
<!-- run code nix
python-stdlib
print(nix_eval_flake("in flake.outputs.devShells.${system}.default.name"))
-->
"""
    )

    assert "nix-shell" == run_process(runnable)


def test_zz_process_file():  # zz to make sure it's the last test
    result = process_file(Path("./example.md"))
    golden = Path("./example_golden.md").read_text()

    assert golden == result

    # process it again, the output should not change

    again = process(result)
    assert again == golden == result


if __name__ == "__main__":
    sys.exit(pytest.main())
