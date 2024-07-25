# Yolo_Klassifikation

Dieses Projekt bietet eine Bildklassifizierungs-App für YOLO (You Only Look Once).
Das Backend wird von einem Flask-Server bereitgestellt unter python 3.9.
Das Frontend wird mit HTML, CSS und JavaScript erstellt.

Es wird empfohlen eine NVidea Graphikkarte zu haben, da dies die Berechnugen erheblich beschleunigen kann.

## Installation
Es wird [Miniconda](https://docs.conda.io/en/latest/miniconda.html) genutzt, um die Installation zu vereinfachen.

1. Klone das Repository:
   ```sh
   git clone https://github.com/dein-benutzername/dein-repository.git
   cd dein-repository
   ```

2. Erstelle die Conda-Umgebung:
   ```sh
   conda env create -f environment.yml
    ```

3. Aktiviere die Umgebung:
   ```sh
   conda activate Yolo_Klassifikation
    ```

4. Starte die app:
    ```sh
    python app.py
    ```

5. Öffne den Browser unter 127.0.0.1:8222
    Viel Spaß =)

## Häufige Probleme

### CUDA
Cuda bereitet mir gerne Kopfschmerzen.
Sollte bei der ausführung der APP 
```sh
WARNING - CUDA is not available. Expect reduced performance.
```
kommen, Sie aber eine CUDA fähige Grafikkarte haben,
so emphele ich folgende Schritte innerhalb der Conda Umgebung:
1. **PyTorch deinstallieren:**
    ```sh
    conda uninstall pytorch
    ```
2. **PyTorch über pip neu installieren**
    Bitte prüfe die Homepage von pytorch.
    [Webseite zu Pytorch](https://pytorch.org/)
    Für meine Geräte gilt:
    ```sh
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```
Sollte es danach noch immer nicht funktionieren, prüfe deine Gerätkonfiguration und versuche eine andere pytorch installation.


