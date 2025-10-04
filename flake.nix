{
  description = "Declarative jellyfin with more options";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };
  outputs = _: {
    nixosModules = rec {
      declarative-jellyfin = import ./modules;
      default = declarative-jellyfin;
    };
  };
}
