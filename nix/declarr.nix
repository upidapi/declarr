{
  python3,
  fetchFromGitHub,
}: let
  profilarr = python3.pkgs.buildPythonPackage rec {
    pname = "profilarr";
    version = "1.1.3";
    pyproject = true;

    src = fetchFromGitHub {
      owner = "Dictionarry-Hub";
      repo = "profilarr";
      rev = "main";
      hash = "sha256-sTQDu8RR+x09BMki/+/PiSy56Inwfu4b+/h81S//Ecs=";
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

    propagatedBuildInputs = with python3.pkgs; [
      flask
      pyyaml
      requests
      gitpython
      regex
    ];

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
    version = "0.8.0b1";
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
