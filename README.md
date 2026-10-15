# Medved

## The idea

Insert comments into markdown file containing commands.
Medved parses this and pastes the stdout after the comment.

```markdown
<!-- run code shell
bash
echo hello
-->
```

<!-- run code shell
bash
echo hello
-->

```shell
hello
```

See <./example.md> for raw markdown and <./example_golden.md> for post-processed examples

<!-- END -->

The syntax is:
```markdown
<!-- run <output format> <param>
<command>
<program of the command passed as stdin>
-->
```

### Output format: Code

Wraps the stdout into markdown code blocks with `<param>` as the syntax highlight string

```
<!-- run code text
python
print("hello")
-->
```

Produces
~~~
```text
hello
```
~~~

### Output format: List

Splits the stdout on newlines and pastes a markdown bullet list

```
<!-- run list
bash
echo hello
echo world
-->
```

Produces
```
- hello
- world
```
