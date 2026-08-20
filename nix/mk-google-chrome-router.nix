{
  browser,
  pkgs,
  extensionId ? "endghlnlmklkignebibikdpnlhojaglb",
  launcherName ? "chrome-url-router-browser",
}:

let
  inherit (pkgs) lib;
  nativeHostName = "dev.so1ve.chrome_url_router";
  host = pkgs.callPackage ./native-host.nix { };
  launcher = pkgs.writeShellApplication {
    name = launcherName;
    text = ''
      export CHROME_URL_ROUTER_BROWSER=${lib.escapeShellArg (lib.getExe browser)}
      exec ${lib.getExe host} open "$@"
    '';
  };
  nativeMessagingHostManifest = pkgs.writeText "${nativeHostName}.json" (
    builtins.toJSON {
      name = nativeHostName;
      description = "Routes external URLs to an existing normal Chrome window";
      path = lib.getExe host;
      type = "stdio";
      allowed_origins = [ "chrome-extension://${extensionId}/" ];
    }
  );
in
{
  inherit
    extensionId
    host
    launcher
    nativeHostName
    nativeMessagingHostManifest
    ;
}
