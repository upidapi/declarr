{
  config,
  lib,
  pkgs,
  ...
}: let
  inherit (lib) mkOption types mkEnableOption;
  # inherit (my_lib.opt) mkEnableOpt;
  cfg = config.services.declarr;
in {
  options.services.declarr = {
    enable = mkEnableOption "buildarr";

    user = lib.mkOption {
      type = lib.types.str;
      default = "declarr";
      description = "User account under which Declarr runs.";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "declarr";
      description = "Group under which Declarr runs.";
    };

    config = mkOption {
      type = types.attrs;
      default = {};
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.buildarr = {
      after = [
        "network.target"

        "qbittorrent.service"
        "sonarr.service"
        "radarr.service"
        "prowlarr.service"
      ];
      wantedBy = ["multi-user.target"];
      serviceConfig = {
        User = cfg.user;
        Group = cfg.group;
        Restart = "on-failure";
        ExecStart = let
          configFile =
            pkgs.writeText
            "config.yaml"
            (builtins.toJSON cfg.settings);
        in
          pkgs.writeScript "declarr-init" "declarr ${configFile}";
      };
    };
  };
}
