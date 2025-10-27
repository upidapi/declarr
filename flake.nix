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
      declarr = import ./nix/modules.nix;
      default = declarr;
    };

    devShells = forAllSystems (
      system: let
        pkgs = import inputs.nixpkgs {inherit system;};
        declarr = pkgs.callPackage ./nix/declarr.nix {};
      in {
        default = pkgs.mkShell {
          name = "declarr-dev";
          inputsFrom = [declarr];
          # packages = with pkgs; [];
        };
      }
    );

    packages = forAllSystems (system: let
      pkgs = import inputs.nixpkgs {inherit system;};
    in {
      declarr = pkgs.callPackage ./nix/declarr.nix {};
    });
  };
}
