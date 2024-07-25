import torch
import torchvision
import pytorch_wavelets as wavelets
import pywt
import hashlib
import numpy as np
import cv2
import logging

from PIL import Image
from torchvision import transforms
from typing import Union


class image_handel:

    transform = transforms.Compose([
        transforms.Resize((1000, 2000)),
        transforms.ToTensor()
    ])
    
    dwt_forward = wavelets.DWTForward(J=1, wave='bior1.3')


    def __init__(self, path, cuda=None, wavelet='bior1.3', from_cv2=False):
        """ 
        :param path: Pfad zur Bilddatei
        :param cuda: True, wenn CUDA verwendet werden soll, False, wenn nicht, None, wenn automatisch entschieden werden soll
        :param wavelet: Das Wavelet, das verwendet werden soll
        """
        self.wavelet = wavelet
        if self.wavelet != "bior1.3":
            image_handel.dwt_forward = wavelets.DWTForward(J=1, wave=self.wavelet)
        self.path = path
        if (torch.cuda.is_available() and cuda is None) or (cuda is True):
            self.cuda = True
        else:
            self.cuda = False
        try:
            if from_cv2:
                self.image = path
            else:
                self.image = Image.open(path)

            self.timage = self.transform(self.image)
            self.dwt = image_handel.dwt_forward
            if self.cuda:
                self.timage = self.timage.cuda()
                self.dwt = self.dwt.cuda()
            self.timage = self.timage.unsqueeze(0)
        except FileNotFoundError as e:
            logging.error(f"File not found: {path} -> {e.__class__.__name__}")
        except IOError as e:
            logging.error(f"Error opening file: {path}  -> {e.__class__.__name__}")
        except Exception as e:
            logging.error(f"Error opening file: {path} -> {e.__class__.__name__}: {e}")
        
        
    def get_image(self)->Image:
        """
        :return: Das Bild als PIL.Image
        """
        return self.image
    
    def get_cv_image(self)->np.ndarray:
        """
        :return: Das Bild als cv2-Image
        """
        return cv2.cvtColor(np.array(self.image), cv2.COLOR_RGB2BGR) 
        
    
    def get_timage(self)->torch.Tensor:
        """
        :return: Das Bild als Tensor
        """
        return self.timage
    
    def compare_image(self, image: "image_handel")-> Union[torch.Tensor, None]:
        """
        :param image: Das Bild, mit dem verglichen werden soll als image_handel-Objekt
        :return: Die Distanz zwischen den Bildern
        :return: None, wenn ein Fehler aufgetreten ist

        Diese Funktion vergleicht zwei Bilder miteinander und gibt die Distanz zwischen den Bildern zurück.
        Beachte dabei, dass image ein image_handel-Objekt sein muss!
        """
        if not self.cuda:
            coeffs1 = pywt.dwt2(image.get_image(), wavelet= self.wavelet)
            coeffs2 = pywt.dwt2(self.image, wavelet=self.wavelet)
            LL1, (LH1, HL1, HH1) = coeffs1
            LL2, (LH2, HL2, HH2) = coeffs2
            train_1 = torch.tensor(LL1)
            train_2 = torch.tensor(LL2)
            distance = torch.dist(train_1, train_2, p=2)
            del coeffs1, coeffs2, LL1, LL2, LH1, LH2, HL1, HL2, HH1, HH2, train_1, train_2
            return distance

        timage2 = image.get_timage()
        
        try:
            coeffs1 = self.dwt(self.timage)
            coeffs2 = self.dwt(timage2)
        except IndexError as e:
            logging.error(f"Error: {e} -> {self.__class__.__name__} -> compare_image")
            return None
        except Exception as e:
            logging.error(self.__class__.__name__,"compare_image ->", "Error:", e.__class__.__name__ + ":", e)
            return None

        flat_coeffs1 = self.__flatten_coeffs_recursive(coeffs1)
        flat_coeffs2 = self.__flatten_coeffs_recursive(coeffs2)
        distance = torch.dist(flat_coeffs1, flat_coeffs2, p=2)

        del coeffs1, coeffs2, flat_coeffs1, flat_coeffs2
        return distance

    def is_equal_image(self, other_image: "image_handel", ok_distance: float = 10.0) -> bool:
        """
        Überprüft, ob zwei Bilder als gleich angesehen werden können.

        :param other_image: Das andere Bild zum Vergleich (image_handel-Objekt).
        :param ok_distance: Der Schwellenwert für die Distanz, ab dem Bilder als gleich gelten.
        :return: True, wenn die Bilder gleich sind, False sonst.
        """
        distance = self.compare_image(other_image)
        if distance is None:  # Fehler bei der Berechnung der Distanz
            return False
        return distance <= ok_distance

    def is_equal_image_fast(self, other_image: "image_handel") -> bool:
        """
        Überprüft, ob zwei Bilder als gleich angesehen werden können indem es
        hashes verwendet. Das ist zwar nicht so genau, aber sollte reichen.

        :param other_image: Das andere Bild zum Vergleich (image_handel-Objekt).
        :return: True, wenn die Bilder gleich sind, False sonst.
        """
        hash1 = self.hash_image()
        hash2 = other_image.hash_image()
        return hash1 == hash2
        

    def hash_image(self)->str:
        """
        :return: Der Hash des Bildes oder ein leerer String, wenn ein Fehler auftritt.
        """
        try:
            coeffs = self.dwt(self.timage)
            flat_coeffs = self.__flatten_coeffs_recursive(coeffs)
            tensor_bytes = flat_coeffs.cpu().numpy().tobytes()
            ret = hashlib.sha256(tensor_bytes).hexdigest()
            del coeffs, flat_coeffs, tensor_bytes
            return ret
        except Exception as e:
            logging.error(self.__class__.__name__,"hash_image ->", "Error:", e.__class__.__name__ + ":", e)
            return ""

    @staticmethod
    def from_cv2_image(image, cuda:bool = None, wavelet='bior1.3')->"image_handel":
        """
        :param image: Das Bild als cv2-Image
        :param cuda: True, wenn CUDA verwendet werden soll, False, wenn nicht, None, wenn automatisch entschieden werden soll
        :param wavelet: Das Wavelet
        :return: Das image_handel-Objekt
        """
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return image_handel(image, cuda=cuda, wavelet=wavelet, from_cv2=True)
    
    @staticmethod
    def hash_image_from_path(path:str,cuda:bool = None)->str:
        """
        :param path: Pfad zur Bilddatei
        :param cuda: True, wenn CUDA verwendet werden soll, False, wenn nicht, None, wenn automatisch entschieden werden soll
        :return: Der Hash des Bildes
        Du kannst diese Funktion verwenden, um den Hash eines Bildes zu bekommen, ohne ein image_handel-Objekt zu erstellen.
        """
        image = image_handel(path, cuda=cuda)
        return image.hash_image()
    
    @staticmethod
    def __flatten_coeffs_recursive(coeffs)->torch.Tensor:
            flat_list = []
            for c in coeffs:
                if isinstance(c, tuple):
                    flat_list.extend(image_handel.__flatten_coeffs_recursive(c))
                elif isinstance(c, torch.Tensor):
                    flat_list.append(c.view(-1))
            return torch.cat(flat_list)