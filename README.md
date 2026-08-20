# Chrome URL Router

> [!WARNING]
>
> Vibe coded. DO NOT USE if you are not comfortable.

Open external links in the last focused normal Chrome window instead of a PWA window.

## Install on Linux

Requires Python 3.9+ and Google Chrome or Chromium.

```console
python3 scripts/install.py
```

Then:

1. Open `chrome://extensions` and enable developer mode.
2. Choose **Load unpacked** and select `extension/`.
3. Select **Chrome URL Router** as the default browser, or run:

   ```console
   xdg-settings set default-web-browser chrome-url-router.desktop
   ```

For Chromium add `--browser chromium`; uninstall with `python3 scripts/install.py uninstall`.

## Nix

Add the flake input:

```nix
inputs.chrome-url-router = {
  url = "github:so1ve/chrome-url-router";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

Then configure Home Manager:

```nix
{ inputs, lib, pkgs, ... }:
let
  router = inputs.chrome-url-router.lib.mkGoogleChromeRouter {
    inherit pkgs;
    browser = pkgs.google-chrome;
  };
  mimeTypes = [
    "application/xhtml+xml"
    "text/html"
    "x-scheme-handler/http"
    "x-scheme-handler/https"
  ];
in
{
  home.packages = [
    pkgs.google-chrome
    router.launcher
  ];
  home.sessionVariables.BROWSER = lib.getExe router.launcher;

  xdg.configFile."google-chrome/NativeMessagingHosts/${router.nativeHostName}.json".source =
    router.nativeMessagingHostManifest;

  xdg.desktopEntries.chrome-url-router = {
    name = "Chrome URL Router";
    exec = "${lib.getExe router.launcher} %U";
    noDisplay = true;
    terminal = false;
    mimeType = mimeTypes;
  };

  xdg.mimeApps = {
    enable = true;
    defaultApplications = lib.genAttrs mimeTypes (_: "chrome-url-router.desktop");
  };
}
```

The Chrome extension is still installed manually as described above.
