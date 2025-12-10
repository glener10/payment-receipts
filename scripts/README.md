Check dependencies and environment in [README.md](../README.md)

#### 🐍 **remove_empty_dirs.py**

```
$ python scripts/remove_empty_dirs.py -i output
```

#### 🐍 **create_coordinates.py**

This system masks sensitive data on payment receipts using template matching. It compares the visual structure of each file with pre-configured templates and applies the corresponding masking coordinates.

Folder structure for new coordinates configs

```
src/config/coordinates/
├── nu/
│   ├── coordinates_output_a.json
│   ├── coordinates_output_a.png
│   ├── coordinates_output_b.json
│   └── coordinates_output_b.png
├── bradesco/
│   ├── coordinates_output_a.json
│   └── coordinates_output_a.png
└── [others]/
    └── ...
```

-   **`.json`**: Coordinates of sensitive areas
-   **`.png` || `.pdf`**: Reference image (masked)

To create a new config use:

```bash
$ python scripts/create_coordinates.py -i 'INPUT_PATH'
```

Steps:

1. Draw rectangles over the sensitive data
2. Press **'q'** to exit
3. The following will be generated:

-   `coordinates_output.json` - coordinates
-   `coordinates_output.png` - masked image

move files to `src/config/coordinates/BANK/`

### 🐍 **count.py**

To count how many payment receipts we have in

Ensure that the database structure is as follows:

```
├── Joao/
│   └── nu/
│       └── receipt-Joao.png
├── Maria/
│   ├── inter/
│   │   └── receipt-Maria.pdf
│   └── sicredi/
│       └── receipt2-Maria.pdf
```

To exec:

```
$ python scripts/count.py -i 'INPUT_FOLDER_PATH'
```

### 🐍 **file_organizer.py**

The result of the Google form search is a folder containing all the collected files in this format:

FILE_NAME-NAME_SENDER.EXTENSION

Exec with:

```
$ python scripts/file_organizer.py -i "INPUT_FOLDER_PATH" -o "OUTPUT_FOLDER_PATH"
```

Example output structure:

```
├── Joao/
│   └── receipt-Joao.png
├── Maria/
│   ├── receipt-Maria.pdf
│   └── receipt2-Maria.pdf
```

### 🐍 **sortition.py**

To draw a user's name

Ensure that the database structure is as follows:

```
├── Joao/
│   └── nu/
│       └── receipt-Joao.png
├── Maria/
│   ├── inter/
│   │   └── receipt-Maria.pdf
│   └── sicredi/
│       └── receipt2-Maria.pdf
```

To exec:

```
$ python scripts/sortition.py -i 'INPUT_FOLDER_PATH'
```
