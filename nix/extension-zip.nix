{
  python3,
  runCommand,
}:

let
  version = (builtins.fromJSON (builtins.readFile ../extension/manifest.json)).version;
in
runCommand "chrome-url-router-extension-${version}.zip" { nativeBuildInputs = [ python3 ]; } ''
  python ${../scripts/package-extension.py} \
    --extension-dir ${../extension} \
    "$out"
''
