# Medved

This file is parsed as part of the python tests.
Reader should open this in raw mode to see the comments

## Run python code, format output as code

<!-- run code text
python
print("hello")
print("world")
-->

## Run bash commands, format output as list

<!-- run list
bash
echo line1
echo line2
-->

## Output format as plain text (no formatting)

<!-- run text
bash
echo "- [ ] Open task"
echo "- [x] Done"
-->

## Stdlib with Nix

Passing `python-stdlib` as the command makes the code `eval()` with some functions to eval/parse nix available.

### nix_eval
<!-- run code text
python-stdlib
print(nix_eval("1+1"))
-->

### nix_eval_flake

Prepares a `nix eval` expression with available:
- `flake` loaded from current directory
- `system`
- `lib`
- `pkgs` if `nix_eval_flake(..., pkgs=True)`

Expression must contain `in`. Allows the user to add more lines to the `let-expression`.

<!-- run code text
python-stdlib
nix = """\
devshell = flake.outputs.devShells.${system}.default;
in
devshell
"""
print(nix_eval_flake(nix))
-->

### Eval on Nix file

Examples to parse a nix file <./users.nix>.
Contents of the file:
<!-- run code nix
bash
cat ./users.nix
-->

#### Without flake, result is code block

The command programs are passed as stdin, and Nix does not allow reading eval from stdin, so using `"$(cat)"` here

<!-- run code nix
nix eval --impure --raw --expr "$(cat)"
let
lib = import <nixpkgs/lib>;
result = (import ./users.nix) { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames result.users.users)
-->

### Without flake, result is a list

<!-- run list
nix eval --impure --raw --expr "$(cat)"
let
lib = import <nixpkgs/lib>;
result = (import ./users.nix) { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames result.users.users)
-->

#### With flake, result is code block

<!-- run code nix
python-stdlib
nix = """
users = import ./users.nix { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames users.users.users)
"""
print(nix_eval_flake(nix))
-->

### With flake, result is a list

<!-- run list
python-stdlib
nix = """
users = import ./users.nix { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames users.users.users)
"""
print(nix_eval_flake(nix))
-->

## Eval pkgs.hello (slow)

Evaluating pkgs is always a bit slower

<!-- run list
python-stdlib
print(nix_eval_flake("in pkgs.hello.pname", pkgs=True))
print(nix_eval_flake("in pkgs.hello.version", pkgs=True))
print(nix_eval_flake("in pkgs.hello", pkgs=True))
-->
