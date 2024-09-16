#!/bin/bash

# Determine the user's shell and profile files
SHELL_NAME=$(basename "$SHELL")
if [ "$SHELL_NAME" = "zsh" ]; then
  SHELL_PROFILE="$HOME/.zshrc"
  SHELL_LOGIN_PROFILE="$HOME/.zprofile"
elif [ "$SHELL_NAME" = "bash" ]; then
  SHELL_PROFILE="$HOME/.bashrc"
  SHELL_LOGIN_PROFILE="$HOME/.bash_profile"
else
  echo "Unsupported shell: $SHELL_NAME"
  SHELL_PROFILE="$HOME/.zshrc"  # Default to zsh profiles
  SHELL_LOGIN_PROFILE="$HOME/.zprofile"
fi

# Install Xcode Command Line Tools if not already installed
if ! xcode-select -p &>/dev/null; then
  echo "Xcode Command Line Tools not found. Installing..."
  xcode-select --install
  # Wait until the installation is complete
  until xcode-select -p &>/dev/null; do
    sleep 5
  done
fi

# Install pyenv and pyenv-virtualenv via pyenv-installer if not already installed
if [ ! -d "$HOME/.pyenv" ]; then
  echo "Installing pyenv and pyenv-virtualenv via pyenv-installer..."
  curl https://pyenv.run | bash
else
  echo "pyenv is already installed. Skipping installation."
fi

# Add pyenv to PATH and initialize in current shell
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
else
  echo "Error: pyenv command not found after installation."
  exit 1
fi

# Add pyenv init to shell startup files
# Add to shell login profile (~/.zprofile)
if ! grep -qs 'pyenv init' "$SHELL_LOGIN_PROFILE"; then
  echo "Configuring $SHELL_LOGIN_PROFILE..."
  {
    echo ''
    echo '# Pyenv configuration'
    echo 'export PYENV_ROOT="$HOME/.pyenv"'
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
    echo 'eval "$(pyenv init --path)"'
  } >> "$SHELL_LOGIN_PROFILE"
fi

# Add to shell interactive profile (~/.zshrc)
if ! grep -qs 'pyenv init' "$SHELL_PROFILE"; then
  echo "Configuring $SHELL_PROFILE..."
  {
    echo ''
    echo '# Pyenv configuration'
    echo 'eval "$(pyenv init -)"'
    echo 'eval "$(pyenv virtualenv-init -)"'
  } >> "$SHELL_PROFILE"
fi

# Install the desired Python version if not already installed
PYTHON_VERSION=3.10.9
if ! pyenv versions --bare | grep -q "^$PYTHON_VERSION$"; then
  echo "Installing Python $PYTHON_VERSION..."
  pyenv install $PYTHON_VERSION
fi

# Create and activate a virtual environment
VENV_NAME=310
if ! pyenv virtualenvs --bare | grep -q "^$VENV_NAME$"; then
  echo "Creating virtual environment $VENV_NAME..."
  pyenv virtualenv $PYTHON_VERSION $VENV_NAME
fi
pyenv activate $VENV_NAME

# Upgrade pip and install Python packages
echo "Upgrading pip and installing Python packages..."
pip install --upgrade pip
pip install opencv-python pandas matplotlib seaborn pyarrow pytz pyserial PyYAML pillow PyQt5
