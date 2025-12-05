import os
from gdown import download_folder

os.makedirs(f'./resultados', exist_ok=True)
links = {"pequena": {"alcione": "https://drive.google.com/drive/folders/1hM4rokn48nKzxufrpZX61fFUxTQDu7bs?usp=sharing",
                     "cartola": "https://drive.google.com/drive/folders/1fZv4J_8UkZme50Lg6610W86z560ib0ke?usp=drive_link",
                     "chicobuarque": "https://drive.google.com/drive/folders/173TyaDOJ5azMK9ZxhbthUZtnYdPg_7_o?usp=drive_link",
                     "djavan": "https://drive.google.com/drive/folders/1xLJNlZgCqb1efYTiia_iYA3ceK0epLKq?usp=drive_link",
                     "seujorge": "https://drive.google.com/drive/folders/1eJmJz8HejnHTQaUrxVmUYPzsFnPNAfIZ?usp=drive_link"},
         "media": {"alcione": "",
                   "cartola": "",
                   "chicobuarque": "",
                   "djavan": "",
                   "seujorge": ""},
         "grande": {"alcione": "",
                    "cartola": "",
                    "chicobuarque": "",
                    "djavan": "",
                    "seujorge": ""},
         "rush": {"alcione": "",
                  "cartola": "",
                  "chicobuarque": "",
                  "djavan": "",
                  "seujorge": ""}}

for instancia in links:
    os.makedirs(f'./resultados/{instancia}', exist_ok=True)
    for grupo in links[instancia]:
        url = links[instancia][grupo]
        if url:
            os.makedirs(f'./resultados/{instancia}/{grupo}', exist_ok=True)
            print(f'Downloading results for {instancia} - {grupo}...')
            download_folder(url=url,
                            output=f'./resultados/{instancia}/{grupo}',
                            quiet=False,
                            use_cookies=True)