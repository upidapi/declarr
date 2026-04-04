{
  python3,
  fetchFromGitHub,
}: let
  profilarr = python3.pkgs.buildPythonPackage rec {
    pname = "profilarr";
    version = "v1.1.4";
    pyproject = true;

    src = fetchFromGitHub {
      owner = "Dictionarry-Hub";
      repo = "profilarr";
      rev = version;
      hash = "sha256-7aiLj87huvSYAuIxcMhudWDAGV3F9QhH1VbLEvB8UyQ=";
    };

    unpackPhase = ''
      cp -r ${src}/backend/app ./profilarr
    '';
    postPatch = ''
      cat >> pyproject.toml <<EOF
        [build-system]
        requires = ["setuptools>=42","wheel"]
        build-backend = "setuptools.build_meta"


        [project]
        name = "profilarr"
        version = "${version}"
        dependencies = []

        [tool.setuptools.packages.find]
        include = ["profilarr*"]
      EOF
    '';

    nativeBuildInputs = with python3.pkgs; [
      setuptools
    ];

    propagatedBuildInputs = with python3.pkgs;
      [
        flask
        pyyaml
        requests
        gitpython
        regex
      ]
      ++ (with pkgs; [
        pkgs.seerr
      ]);

    pythonImportsCheck = [
      "profilarr"
    ];

    meta = {
      description = "";
    };
  };
in
  python3.pkgs.buildPythonApplication {
    pname = "declarr";
    version = "0.1.0";
    pyproject = true;

    src = ../.;

    nativeBuildInputs = with python3.pkgs; [
      setuptools
    ];

    propagatedBuildInputs = with python3.pkgs; [
      requests
      pyyaml
      jsonpath-ng
      urllib3

      profilarr
    ];

    # pythonImportsCheck = [
    # ];

    meta = {
      description = "Declarative configuration for the *arr stack";
      mainProgram = "declarr";
    };
  }
