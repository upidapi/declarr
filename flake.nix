{
  description = "Declarative jellyfin with more options";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    systems.url = "github:nix-systems/default";
  };
  outputs = {...} @ inputs: let
    forAllSystems = inputs.nixpkgs.lib.genAttrs (import inputs.systems);
  in {
    nixosModules = rec {
      declarr = import ./modules.nix;
      default = declarr;
    };
    packages = forAllSystems (system: let
      pkgs = import inputs.nixpkgs {inherit system;};
    in {
      declarr = pkgs.callPackage ./declarr.nix {};
    });
  };
}
