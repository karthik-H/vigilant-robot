# Httpie
Test project for fault localization


Bug Information: https://github.com/httpie/cli/commit/589887939507ff26d36ec74bd2c045819cfa3d56

Bug Location: https://github.com/ProjectEminence/Httpie/blob/5bea48194f4780d0892c9b4dfdbe47bd9bfc91ac/httpie/sessions.py#L104


# How to setup pytest
Python 3.8

- pip install -r bugsinpy_requirements.txt
- pip install . //to install the httpie package(source to test)
- pytest