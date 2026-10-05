# SPI_gui

For academic usage in Okada Lab, Tokyo Tech only.

## Introduction

This is an implementation of SPI master of Okada Lab's private SPI protocol.

For the detailed protocol and the implementation of the on-chip SPI slave, see the below path.
You may need to connect to the libra server of Okada Lab.

`\\libra\public\10Tapeout\tsmc65nm\SPI制御ソフト\SPI-Slave仕様_v4.pptx`

## Installation (For developer only)

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

## SPI Control (register array, preview)

`SpiControl.py` is a new GUI next to `GuiMain.py` (which is unchanged). Instead of a table it draws
every register as a tile: click a bit to flip it, click the value to type one (decimal, `0x…`, `0b…`).

```bash
python SpiControl.py [profile.json | old table .csv/.xlsx/.xlsm]
```

* **Profile** — the only chip-specific input: protocol, chips (link + chip select, plus chip address
  for CA), register addresses and widths, optional field names. Old tables open directly
  (File ▸ Open) and can be saved as a profile (File ▸ Save profile as…).
* **Watches** replace the ShortCutList and the Picker: buses are found from field names such as
  `FLL_KP<0>`; others are picked by clicking bits on the tiles (with an optional binary point).
* **Links** — NI USB-8452, Raspberry Pi Pico W boards (Discover), each chip routed to one link.
  *Links ▸ Simulate hardware* runs everything against in-memory chips.
* Edits stay unsent until *Write*; *Auto-write* sends each change at once.

A minimal profile:

```json
{"name": "New chip", "protocol": "classic",
 "chips": [{"label": "SS0", "link": "ni", "ss": 0}, {"label": "SS1", "link": "pico:#1", "ss": 1}],
 "registers": [{"addr": "1-60", "width": 5},
               {"addr": 13, "fields": [{"name": "reset", "lo": 0}, {"name": "FLL_en", "lo": 2}]},
               {"addr": "111-116", "width": 13, "ro": true}],
 "watches": [{"name": "MY_BUS", "range": "A15[1:0], A14[4:3]"}]}
```

Code layout: `spi_model.py` (profiles, values, operations; no Qt), `spi_links.py` (NI / Pico /
simulator), `spi_widgets.py` and `spi_panels.py` (GUI). Tests: `python -m unittest discover tests`.

## Usage

Detailed usage may see the following file. Although it is a little bit outdated,
it still works.

`\\libra\public\11Meas\SPIGUI\SPI_NI845_MANUAL.pptx`
