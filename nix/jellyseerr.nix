{
  config,
  lib,
  pkgs,
  ...
}: let
  inherit
    (lib)
    mkOption
    types
    mkIf
    ;

  cfg = config.services.jellyseerr;
in {
  options.services.jellyseerr = {
    config = mkOption {
      type = types.attrs;
      default = {};
    };
    # for compat
    dataDir = lib.mkOption {
      type = lib.types.path;
      readOnly = true;
      default = cfg.configDir;
    };
  };

  config = let
    jellyseerr-cfg = {
      jellyseerr =
        lib.recursiveUpdate {
          declarr = {
            type = "jellyseerr";
            inherit (cfg) port;
            stateDir = cfg.configDir;
          };
        }
        cfg.config;
    };
    cfg-file =
      pkgs.writeText
      "jellyseerr-config.yaml"
      (builtins.toJSON jellyseerr-cfg);

    pkg = pkgs.callPackage ./declarr.nix {};

    jellyseerr-init = pkgs.writeShellApplication {
      name = "jellyseerr-init";
      runtimeInputs = [cfg.package];
      checkPhase = ''
        runHook preCheck
        runHook postCheck
      '';
      text = ''
        ${lib.getExe pkg} \
          --sync \
          --run jellyseerr \
          ${cfg-file}
      '';
    };
  in
    mkIf cfg.enable {
      systemd.services.jellyseerr = {
        wants = ["declarr.service"];
        after = ["jellyfin.service" "sonarr.service" "radarr.service" "declarr.service"];
        serviceConfig = {
          # DynamicUser = false;
          ExecStart = lib.mkForce (lib.getExe jellyseerr-init);
        };
      };
    };
}
