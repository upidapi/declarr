{
  python3,
}:
python3.pkgs.buildPythonApplication rec {
  pname = "buildarr";
  version = "0.8.0b1";
  pyproject = true;

  src = ./.;

  nativeBuildInputs = with python3.pkgs; [
    setuptools
  ];

  propagatedBuildInputs = with python3.pkgs; [
    requests
    pyyaml
    jsonpath-ng
    urllib3
  ];

  # pythonImportsCheck = [
  #   "buildarr"
  # ];

  meta = {
    description = "Declarative configuration for the *arr stack";
    # homepage = "https://github.com/buildarr/buildarr";
    # license = lib.licenses.gpl3Only;
    # maintainers = with lib.maintainers; [hierocles];
    mainProgram = "declarr";
  };
}
