{ lib, ... }:

let
  users = {
    bob = { };
    alice = { };
    root = { };
  };
in
{
  users.users = {
    "root" = { };
  }
  // lib.mapAttrs
    (
      name: user:
        user
    )
    users;
}
