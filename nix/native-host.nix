{
  lib,
  python3,
  writeTextFile,
}:

writeTextFile {
  name = "chrome-url-router";
  destination = "/bin/chrome-url-router";
  executable = true;
  text = builtins.replaceStrings [ "#!/usr/bin/env python3\n" ] [ "#!${lib.getExe python3}\n" ] (
    builtins.readFile ../src/chrome-url-router.py
  );
  meta = {
    description = "Route external URLs to an existing normal Chrome window";
    mainProgram = "chrome-url-router";
    platforms = lib.platforms.linux;
  };
}
