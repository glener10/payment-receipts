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
