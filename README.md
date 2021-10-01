# SPI_gui

For academic usage in Okada Lab, Tokyo Tech only.

## Introduction

This is an implementation of SPI master of Okada Lab's private SPI protocol.

For the detailed protocol and the implementation of the on-chip SPI slave, see the below path.
You may need to connect to the libra server of Okada Lab.

`\\libra\public\10Tapeout\tsmc65nm\SPI制御ソフト\SPI-Slave仕様_v4.pptx`

## Installation

First of all, if you do not have a Python environment, you can go to
[the official website of Anaconda](https://www.anaconda.com/products/individual)
to download and install.

After the installation of Anaconda, you can:

* Linux/Mac: Open a bash window and then `cd` to the installation path.
* Windows: Open the Anaconda Prompt and then `cd` to the installation path.

### Anaconda

If you are using Anaconda, try first create a virtual environment and install `pip`:

```bash
conda create --name spi_env
conda install pip
```

Then, follow the below section.

### Pip

With the following function, you may need to

```bash
pip install -r requirements.txt
```

## Starting

After installing the environment, you may start the program by running `GuiMain.py`.

To run a Python script, you may need to execute as followings.

### In the Command Line

If you are already in the installation path, run:

```bash
python GuiMain.py
```

### In Python Code Editor

According to your code editor, please refer to:

* Visual Studio Code: https://code.visualstudio.com/docs/python/python-tutorial
* Spyder: https://www.jcchouinard.com/python-with-spyder-ide/

## Usage

Detailed usage may see the following file. Although it is a little bit outdated,
it still works.

`\\libra\public\11Meas\SPIGUI\SPI_NI845_MANUAL.pptx`
