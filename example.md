# Medved

This file is parsed as part of the python tests.
Reader should open this in raw mode to see the comments

## Output modes

### Run python code, format output as code

<!-- run code text
python
print("hello")
print("world")
-->

### Run bash commands, format output as list

<!-- run list
bash
echo line1
echo line2
-->

### Output format as plain text (no auto formatting)

<!-- run text
bash
echo "- [ ] Open task"
echo "- [x] Done"
-->

## Stdlib with Nix

Medved has built-in support for parsing Nix.

Passing `python-stdlib` as the command makes the code `eval()` with some functions to eval/parse nix available.

### nix_eval

The expression is "prepared" with the following available:

- `pkgs` - from `<nixpkgs>`
- `lib`
Comes with `pkgs` and `lib` available.

Runs with `--impure` to alllow importing of other `nix` files relative to the local directory.

Note that `--impure` is slow.

<!-- run code text
python-stdlib
print(nix_eval("in 1+1"))
-->

### nix_eval_flake

Evaluate a nix flake output.

Expects:

- `flake_output` - name of the flake output
  - must begin with `.#`
- `expr` - expression to apply over that output
  - must contain the `in` keyword. Allows the user to declare more variables in the `let` expression.

The expression is "prepared" with the following available:

- `pkgs` - default pkgs
- `lib`

**This is not `--impure`, so it's much faster and preferred for flake evaluation**

Examples:

<!-- run code text
python-stdlib
print(
  nix_eval_flake(".#devShells.x86_64-linux", "in flakeOutput.default.name")
)
-->

<!-- run code text
python-stdlib
print(
  nix_eval_flake(".#nixosConfigurations.example-system", "in flakeOutput.config.networking.hostName")
)
-->

### Stdlib examples

#### `nix_eval`

Examples to parse a nix file <./users.nix>.
Contents of the file:
<!-- run code nix
bash
cat ./users.nix
-->

Eval a basic `nix` expression

<!-- run code
python-stdlib
print(
  nix_eval("in 1+1")
)
-->

Import a nix file and transform the result

<!-- run list
python-stdlib
expr = """\
  imported-users = (import ./users.nix) { inherit lib; };
in
  builtins.concatStringsSep "\n" (builtins.attrNames imported-users.users.users)
"""
print(
  nix_eval(expr)
)
-->

#### `nix_eval_flake`

Evaluate multiple times

<!-- run list
python-stdlib
print(nix_eval_flake(".#legacyPackages.x86_64-linux", "in flakeOutput.hello.pname"))
print(nix_eval_flake(".#legacyPackages.x86_64-linux", "in flakeOutput.hello.version"))
print(nix_eval_flake(".#legacyPackages.x86_64-linux", "in flakeOutput.hello"))
-->

Or combine in one nix expression for faster evaluation

<!-- run list
python-stdlib
expr = """\
  package = flakeOutput.hello;
in
  builtins.concatStringsSep "\n" [ package.pname package.version package ]
"""
print(
  nix_eval_flake(".#legacyPackages.x86_64-linux", expr)
)
-->
