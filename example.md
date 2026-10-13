# Medved

## Run python code
<!-- run code nix
python-stdlib
print(nix_eval("1+1"))
print(nix_eval_flake("in flake.outputs.devShells.${system}.default"))
-->

Above here is the output of the command

## Eval nix code

This will produce a code block

<!-- run code nix
nix eval --impure --raw --expr "$(cat)"
let
lib = import <nixpkgs/lib>;
result = (import ./users.nix) { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames result.users.users)
-->

This gets overwritten

<!-- END -->

Same output using nix stdlib "nix_eval_flake"

<!-- run code nix
python-stdlib
nix = """
users = import ./users.nix { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames users.users.users)
"""
print(nix_eval_flake(nix))
-->

## Eval nix as a list

Produces bullet points

<!-- run list
nix eval --impure --raw --expr "$(cat)"
let
lib = import <nixpkgs/lib>;
result = (import ./users.nix) { inherit lib; };
in
builtins.concatStringsSep "\n" (builtins.attrNames result.users.users)
-->

Same output using nix stdlib "nix_eval_flake"

<!-- run list
python-stdlib
nix = """
in builtins.concatStringsSep "\n" (builtins.attrNames (import ./users.nix { inherit lib; }).users.users)
"""
print(nix_eval_flake(nix))
-->

## Eval pkgs.hello (slow)

<!-- run list
python-stdlib
print(nix_eval_flake("in pkgs.hello.pname", pkgs=True))
print(nix_eval_flake("in pkgs.hello.version", pkgs=True))
print(nix_eval_flake("in pkgs.hello", pkgs=True))
-->
