{
  python3,
}:
python3.pkgs.buildPythonApplication {
  pname = "declarr";
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
  # ];

  meta = {
    description = "Declarative configuration for the *arr stack";
    mainProgram = "declarr";
  };
}
