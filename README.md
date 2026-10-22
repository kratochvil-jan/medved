# Medved

## The idea

Dont let your markdown documentation become out of sync.
Embed commands inside markdown comments, which can be executed via git-hooks or in CI.
Medved finds these comments, parses the commands, executes it and pastes the stdout back into the markdown file.

<!-- this code block is ignored by Medved -->
```markdown
<!-- run code shell
bash
echo hello
-->
```

This produces the following output:

<!-- Medved evalates the comment below and pastes the output before the END marker -->
<!-- run code shell
bash
echo hello
-->

```shell
hello
```

<!-- END -->

See <./example.md> for raw markdown and <./example_golden.md> for post-processed examplesfor more

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

### Output format: Text

No formatting applied. Stdout is pasted verbatim

```
<!-- run text
bash
echo "- hello"
echo "world"
-->
```

Produces
```
- hello
world
```
