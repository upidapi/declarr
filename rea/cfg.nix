
{
  config,
  lib,
  mlib,
  const,
  self,
  ...
}: let
  inherit (const) ports ips;
  inherit (lib) mkIf;
  inherit (mlib) mkEnableOpt;
  cfg = config.modules.nixos.homelab.media.jellyseerr;
in {
  options.modules.nixos.homelab.media.jellyseerr = mkEnableOpt "";

  imports = [
    ./base.nix
  ];

  config = mkIf cfg.enable {
    # not needed since the templater has root perms
    sops.secrets = {
      #   "radarr/api-key_jellyseerr" = {
      #     key = "radarr/api-key";
      #     # owner = config.services.jellyseerr.user;
      #     sopsFile = "${self}/secrets/server.yaml";
      #   };
      #   "sonarr/api-key_jellyseerr" = {
      #     key = "sonarr/api-key";
      #     # owner = config.services.jellyseerr.user;
      #     sopsFile = "${self}/secrets/server.yaml";
      #   };
      "jellyseerr/api-key" = {
        key = "jellyseerr/api-key";
        owner = config.services.jellyseerr.user;
        sopsFile = "${self}/secrets/server.yaml";
      };

      "jellyseerr/users/admin/password" = {
        sopsFile = "${self}/secrets/server.yaml";
      };

      "jellyfin/users/admin/password_jellyseerr" = {
        key = "jellyfin/users/admin/password";
        owner = config.services.jellyseerr.user;
        sopsFile = "${self}/secrets/server.yaml";
      };
    };

    # https://www.rapidseedbox.com/blog/jellyseerr-guide#01
    services.jellyseerr = {
      enable = true;
      port = ports.jellyseerr;
      # openFirewall = true;
      force = true;
      group = "media";

      apiKeyFile = config.sops.secrets."jellyseerr/api-key".path;
      jellyfin = {
        email = "videw@icloud.com";
        username = "admin";
        passwordFile = config.sops.secrets."jellyfin/users/admin/password_jellyseerr".path;
      };
      # users.admin = {
      #   email = "videw@icloud.com";
      #   passwordFile = config.sops.secrets."jellyseerr/users/admin/password".path;
      #   permissions = {
      #     admin = true;
      #   };
      #   mutable = false;
      # };
      settings.main.defaultPermissions = {
        request = true;
        request4k = true;
        autoApprove = true;
        autoApprove4k = true;
        autoRequest = true;
      };
      extraSettings = {
        jellyfin = {
          name = "upinix-laptop";
          apiKey = config.sops.placeholder."jellyfin/jellyseerr-api-key";

          ip = "127.0.0.1"; # or url
          port = ports.jellyfin;

          useSsl = false;
          urlBase = "";
          externalHostname = "https://jellyfin.upidapi.dev";
          jellyfinForgotPasswordUrl = "";

          # I don't think this is needed
          # serverId = "cd69c8b59e5b482eacf8ea3ff8c7f5ff";

          libraries = [
            {
              enabled = true;
              # id = "f137a2dd21bbc1b99aa5c0f6bf02a805";
              name = "Movies";
              type = "movie";
            }
            {
              enabled = true;
              # id = "a656b907eb3a73532e40e44b968d0225";
              name = "Shows";
              type = "show";
            }
          ];
        };
        main = {
          apiKey = config.sops.placeholder."jellyseerr/api-key";
          applicationTitle = "Jellyseerr";
          applicationUrl = "";
          cacheImages = false;
          defaultQuotas = {
            movie = {};
            tv = {};
          };
          discoverRegion = "";
          enableSpecialEpisodes = false;
          hideAvailable = false;
          localLogin = true;
          locale = "en";
          mediaServerLogin = true;
          mediaServerType = 2;
          newPlexLogin = true;
          originalLanguage = "";
          partialRequestsEnabled = true;
          streamingRegion = "";
        };
        # plex = {
        #   ip = "";
        #   libraries = [];
        #   name = "";
        #   port = 32400;
        #   useSsl = false;
        # };
        public = {initialized = true;};
        radarr = [
          {
            id = 0;
            name = "radarr";
            apiKey = config.sops.placeholder."radarr/api-key";

            hostname = "127.0.0.1";
            # hostname = ips.mullvad;
            port = ports.radarr;

            externalUrl = "https://radarr.upidapi.dev";
            useSsl = false;

            is4k = false;
            isDefault = true;

            syncEnabled = true;
            preventSearch = false;
            minimumAvailability = "released";

            tags = [];
            tagRequests = false;

            activeDirectory = "/raid/media/movies";
            activeProfileId = 4;
            activeProfileName = "HD-1080p";
          }
        ];
        sonarr = [
          {
            id = 0;
            name = "sonarr";
            apiKey = config.sops.placeholder."sonarr/api-key";

            hostname = "127.0.0.1";
            # hostname = ips.mullvad;
            port = ports.sonarr;

            externalUrl = "https://sonarr.upidapi.dev";
            useSsl = false;

            is4k = false;
            isDefault = true;

            syncEnabled = true;
            preventSearch = false;
            enableSeasonFolders = true;

            tags = [];
            animeTags = [];
            tagRequests = false;

            activeDirectory = "/raid/media/tv";
            activeProfileId = 4;
            activeProfileName = "HD-1080p";
          }
        ];
        tautulli = {};
      };
    };
  };
}
