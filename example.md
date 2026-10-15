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

## Stdlib with Nix

Passing `python-stdlib` as the command makes the code `eval()` with some functions to eval/parse nix available.

### nix_eval
<!-- run code text
python-stdlib
print(nix_eval("1+1"))
-->

### nix_eval_flake

Prepares a `nix eval` expression with available:
- `flake`the `flake` loaded,
- `system`
- `lib`
- `pkgs` if `nix_eval_flake(..., pkgs=True)`

Expression should shart with `in`. Allows the user to add more lines to the `let` part of Nix.

<!-- run code text
python-stdlib
print(nix_eval_flake("in flake.outputs.devShells.${system}.default"))
-->

### Eval on Nix file without flake, result is code block

The command programs are passed as stdin, and Nix does not allow reading eval from stdin, so using `"$(cat)"` here
No flakes.

<!-- run code nix
nix eval --impure --raw --expr "$(cat)"
let
lib = import <nixpkgs/lib>;
result = (import ./users.nix) { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames result.users.users)
-->


### Eval on Nix file with flake, result is code block

<!-- run code nix
python-stdlib
nix = """
users = import ./users.nix { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames users.users.users)
"""
print(nix_eval_flake(nix))
-->

### Eval on Nix file without flake, result is a list

<!-- run list
nix eval --impure --raw --expr "$(cat)"
let
lib = import <nixpkgs/lib>;
result = (import ./users.nix) { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames result.users.users)
-->

### Eval on Nix file with flake, result is a list

<!-- run list
python-stdlib
nix = """
in builtins.concatStringsSep "\n" (builtins.attrNames (import ./users.nix { inherit lib; }).users.users)
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
