{
  description = "Open external URLs in the last focused normal Google Chrome window";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      lib.mkGoogleChromeRouter = import ./nix/mk-google-chrome-router.nix;

      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          package = pkgs.callPackage ./nix/native-host.nix { };
          extensionZip = pkgs.callPackage ./nix/extension-zip.nix { };
        in
        {
          default = package;
          chrome-url-router = package;
          extension-zip = extensionZip;
        }
      );

      formatter = forAllSystems (system: nixpkgs.legacyPackages.${system}.nixfmt);
    };
}
