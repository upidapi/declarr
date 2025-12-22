{
  config,
  lib,
  pkgs,
  self',
  ...
}: let
  inherit (lib) mkOption types mkEnableOption mkIf;
  # inherit (my_lib.opt) mkEnableOpt;
  cfg = config.services.declarr;

  mkArrSerivice = name: let
    apiKeyEnvVar = "${lib.toUpper name}__AUTH__APIKEY";
    cfg = config.services.${name};
  in {
    options.services.${name}.apiKeyFile = mkOption {
      type = lib.types.str;
    };
    config.systemd.services.${name}.serviceConfig.ExecStart = mkIf cfg.enable (
      lib.mkForce
      (pkgs.writeShellScript
        "init-${name}" ''
          ${apiKeyEnvVar}=$(cat ${cfg.apiKeyFile}) \
            ${lib.getExe cfg.package} \
            -nobrowser \
            -data="${cfg.dataDir}"
        '')
    );
  };
in {
  imports = [
    ./jellyseerr.nix
    (mkArrSerivice "sonarr")
    (mkArrSerivice "radarr")
    (mkArrSerivice "lidarr")
    (mkArrSerivice "prowlarr")
  ];

  options.services.declarr = {
    enable = mkEnableOption "declarr";

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
    users.users = lib.mkIf (cfg.user == "declarr") {
      declarr = {
        isSystemUser = true;
        group = cfg.group;
      };
    };

    users.groups = lib.mkIf (cfg.group == "declarr") {
      declarr = {};
    };

    systemd.services.declarr = {
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
        StateDirectory = "declarr";

        Type = "oneshot";
        RemainAfterExit = "yes";
        Restart = "on-failure";

        ExecStart = let
          configFile =
            pkgs.writeText
            "config.yaml"
            (builtins.toJSON cfg.config);

          pkg = pkgs.callPackage ./declarr.nix {};
        in
          pkgs.writeShellScript
          "declarr-init"
          "${lib.getExe pkg} --sync ${configFile}";
      };
    };
  };
}
