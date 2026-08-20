# Chrome URL Router

> [!WARNING]
>
> Vibe coded. DO NOT USE if you are not comfortable.

Open external links in the last focused normal Chrome window instead of a PWA window.

## Why?

Chrome owns both regular tabbed windows and installed PWA windows. When another application opens a URL through `xdg-open` or the Chrome command line, there is no option to say “use the last focused regular window.” If a PWA was used most recently, Chrome may create another regular window instead of adding a tab to the regular window you were already using.

Typical symptoms are links appearing in an unexpected window, unnecessary new Chrome windows accumulating, or a timing-based launcher leaving a blank tab or typing into the wrong page. Launchers that focus a window, sleep, and then paste or type the URL are inherently racy: focus can change at any point, and they also depend on the clipboard or synthetic keyboard input.

Chrome URL Router becomes the desktop URL handler and forwards each URL through Native Messaging to its extension. The extension can explicitly find the last focused `normal` Chrome window and create a tab in that window, without a fixed delay, clipboard access, or simulated input.

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
