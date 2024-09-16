@REM runsensors.bat
@echo off
if exist 310\* (
    echo Found Python 3.10 env
  .\310\Scripts\activate.bat
  python -V
  pip -V
  echo Setup is finished
) else (
  echo Python 3.10 not found. Installing...
  py -3.10 -m venv 310
  .\310\Scripts\activate
  python.exe -m pip install --upgrade pip
  python -V
  pip -V
  echo Setting up packages...
  pip install opencv-python
  pip install pandas matplotlib seaborn pyarrow pytz
  pip install pyserial PyYAML pillow
  pip install PyQt5
  echo Setup is finished
)
