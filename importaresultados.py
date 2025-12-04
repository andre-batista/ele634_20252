import os
from gdown import download_folder

os.makedirs(f'./resultados', exist_ok=True)
links = {"pequena": "https://drive.google.com/drive/folders/1Zpu57kWp7bXxLCcOeVg17oxW6AwYpl19?usp=sharing",
         "media": "https://drive.google.com/drive/folders/1wneL7z_ynzNmQtStXWmzTWc5fYqlOUxV?usp=sharing",
         "grande": "https://drive.google.com/drive/folders/1y6F04vQRlqW8pViHc2aXwYIetgNwy27X?usp=sharing",
         "rush": "https://drive.google.com/drive/folders/1FmIERZPkGsh-Ju7JHtP65ovM_0vAzjtF?usp=sharing"}

for instancia, url in links.items():
    os.makedirs(f'./resultados/{instancia}', exist_ok=True)
    download_folder(url, output=f'./resultados/{instancia}', quiet=False, 
                    use_cookies=True)