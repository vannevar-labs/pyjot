{
  description = "Flake for dl-jot python library using uv2nix with hammer overrides";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Add the hammer overrides package
    uv2nix_hammer_overrides = {
      url = "github:TyberiusPrime/uv2nix_hammer_overrides";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
    uv2nix_hammer_overrides,
    ...
  }: let
    inherit (nixpkgs) lib;

    # Define the supported systems
    systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin"];

    # Helper function to generate per-system attributes
    forAllSystems = f: lib.genAttrs systems (system: f system);

    # Load a uv workspace from a workspace root
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};

    # Create package overlay from workspace
    overlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };

    # Create a Python set for each system, now with hammer overrides
    mkPythonSet = system: let
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python3;

      # First create the base Python set with the build systems and workspace overlay
      basePythonSet =
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        })
        .overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
          ]
        );

      # Then apply the hammer overrides and our custom overrides to the host packages
      customOverrides = final: prev: {
        # Add any additional custom overrides here
        psycopg2 = prev.psycopg2.overrideAttrs (old: {
          buildInputs =
            (old.buildInputs or [])
            ++ lib.optionals
            (final.stdenv.hostPlatform.isLinux) [final.postgresql];
        });
      };

      # Get the hammer overrides for this system
      hammerOverrides = uv2nix_hammer_overrides.overrides pkgs;

      # Apply both overrides to the host packages
      pythonSetWithOverrides = basePythonSet.pythonPkgsHostHost.overrideScope (
        lib.composeManyExtensions [
          hammerOverrides
          customOverrides
        ]
      );
    in
      # Return the final set with overrides applied
      pythonSetWithOverrides;
  in {
    # Package a virtual environment for each system
    packages = forAllSystems (system: let
      pythonSet = mkPythonSet system;
    in {
      default = pythonSet.mkVirtualEnv "jot-env" workspace.deps.default;

      # All optional-dependencies enabled
      optionals = pythonSet.mkVirtualEnv "jot-optionals-env" workspace.deps.optionals;

      # dev is the only dependency group so we can use "all" groups
      dev = pythonSet.mkVirtualEnv "jot-dev-env" workspace.deps.groups;

      # All optionals and groups enabled
      all = pythonSet.mkVirtualEnv "jot-all-env" workspace.deps.all;
    });

    # Development shells for each system
    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      pythonSet = mkPythonSet system;
      python = pkgs.python3;

      # Create an overlay enabling editable mode for all local dependencies
      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$REPO_ROOT";
      };

      editablePythonSet = pythonSet.overrideScope (
        lib.composeManyExtensions [
          editableOverlay
          (final: prev: {
            dl-jot = prev.dl-jot.overrideAttrs (old: {
              src = lib.fileset.toSource {
                root = old.src;
                fileset = lib.fileset.unions [
                  (old.src + "/pyproject.toml")
                  (old.src + "/jot")
                  # Include any other necessary files
                ];
              };

              nativeBuildInputs =
                old.nativeBuildInputs
                ++ final.resolveBuildSystem {
                  editables = [];
                };
            });
          })
        ]
      );

      # Build virtual environment with local packages being editable
      virtualenv = editablePythonSet.mkVirtualEnv "dl-jot-dev-env" workspace.deps.optionals;
    in {
      # Impure development shell using uv to manage virtualenvs
      impure = pkgs.mkShell {
        packages = [
          python
          pkgs.uv
        ];
        env =
          {
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = python.interpreter;
          }
          // lib.optionalAttrs (system == "x86_64-linux" || system == "aarch64-linux") {
            LD_LIBRARY_PATH = lib.makeLibraryPath pkgs.pythonManylinuxPackages.manylinux1;
          };
        shellHook = ''
          unset PYTHONPATH
        '';
      };

      # Pure development shell using uv2nix
      default = pkgs.mkShell {
        packages = [
          virtualenv
          pkgs.uv
        ];

        env = {
          UV_NO_SYNC = "1";
          UV_PYTHON = "${virtualenv}/bin/python";
          UV_PYTHON_DOWNLOADS = "never";
        };

        shellHook = ''
          unset PYTHONPATH
          export REPO_ROOT=$(git rev-parse --show-toplevel)
        '';
      };
    });
  };
}
