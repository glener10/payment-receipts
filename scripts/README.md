Check dependencies and environment in [README.md](../README.md)

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
