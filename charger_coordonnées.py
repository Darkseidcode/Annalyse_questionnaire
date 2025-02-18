import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import pytesseract
import json
import os
import pandas as pd

# Définir la variable d'environnement TESSDATA_PREFIX pour localiser les fichiers de langue
os.environ['TESSDATA_PREFIX'] = r"Tesseract-OCR\tessdata"  # Assurez-vous que ce chemin est correct

# Configuration de Tesseract (modifiez le chemin si nécessaire)
pytesseract.pytesseract.tesseract_cmd = r"Tesseract-OCR\tesseract.exe"  # Modifiez si nécessaire

class CanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Analyse des Questionnaires")

        # Créer un frame pour le canvas
        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Canvas pour dessiner les rectangles
        self.canvas = tk.Canvas(self.frame, width=800, height=600, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Boutons pour charger les fichiers
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        self.load_image_button = tk.Button(button_frame, text="Charger les images", command=self.load_images)
        self.load_image_button.pack(side=tk.LEFT, padx=10)

        self.load_json_button = tk.Button(button_frame, text="Charger les coordonnées", command=self.load_json)
        self.load_json_button.pack(side=tk.LEFT, padx=10)

        self.process_button = tk.Button(button_frame, text="Extraction des questions", command=self.process_all_images)
        self.process_button.pack(side=tk.LEFT, padx=10)

        self.export_button = tk.Button(button_frame, text="Exporter vers Excel", command=self.export_to_excel)
        self.export_button.pack(side=tk.LEFT, padx=10)

        self.image_paths = []
        self.coordinates = None
        self.image = None
        self.image_tk = None
        self.results = []

    def load_images(self):
        # Ouvrir le dialogue pour sélectionner les images PNG
        self.image_paths = filedialog.askopenfilenames(title="Choisir des images PNG", filetypes=[("PNG files", "*.png")])
        if self.image_paths:
            self.display_image(0)

    def display_image(self, index):
        if self.image_paths and 0 <= index < len(self.image_paths):
            self.image = Image.open(self.image_paths[index])
            self.image_tk = ImageTk.PhotoImage(self.image)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)
            # Ajuster la région de défilement pour s'adapter à la taille de l'image
            self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height))

    def load_json(self):
        # Ouvrir le dialogue pour sélectionner le fichier JSON
        file_path = filedialog.askopenfilename(title="Choisir un fichier JSON", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                # Lire le fichier JSON
                with open(file_path, 'r') as file:
                    self.coordinates = json.load(file)
                messagebox.showinfo("Succès", "Fichier JSON chargé avec succès.")
                self.display_coordinates()
            except json.JSONDecodeError:
                messagebox.showerror("Erreur", "Le fichier sélectionné n'est pas un fichier JSON valide.")
            except KeyError as e:
                messagebox.showerror("Erreur", f"Clé manquante dans les données JSON: {e}")

    def display_coordinates(self):
        # Effacer le canvas avant de dessiner les coordonnées
        self.canvas.delete("all")
        if self.image_tk:
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)
        
        if self.coordinates:
            for item in self.coordinates:
                # Dessiner le rectangle de la question
                q_coords = item["coordinates"]
                self.canvas.create_rectangle(
                    int(q_coords["start_x"]), int(q_coords["start_y"]),
                    int(q_coords["end_x"]), int(q_coords["end_y"]),
                    outline="blue", width=2
                )
                # Dessiner les rectangles des cases
                for case in item["cases"]:
                    case_coords = case["cases_coordinates"]
                    self.canvas.create_rectangle(
                        int(case_coords["start_x"]), int(case_coords["start_y"]),
                        int(case_coords["end_x"]), int(case_coords["end_y"]),
                        outline="green", width=2
                    )
                    label_coords = case["label_coordinates"]
                    self.canvas.create_rectangle(
                        int(label_coords["start_x"]), int(label_coords["start_y"]),
                        int(label_coords["end_x"]), int(label_coords["end_y"]),
                        outline="red", width=2
                    )

    def process_all_images(self):
        if not self.image_paths:
            messagebox.showerror("Erreur", "Veuillez charger les images.")
            return
        if not self.coordinates:
            messagebox.showerror("Erreur", "Veuillez charger le fichier JSON des coordonnées.")
            return

        self.results = []

        for image_index, image_path in enumerate(self.image_paths):
            print(f"\nTraitement de l'image {image_index + 1} : {os.path.basename(image_path)}")
            result = self.analyze_questionnaire(image_path, self.coordinates)
            self.results.append({"image": f"Image {image_index + 1}", "analysis": result})

        self.display_results(self.results)

    def analyze_questionnaire(self, image_path, coordinates):
        image = cv2.imread(image_path)
        results = []

        for item in coordinates:
            print(f"Analyse de la question avec les coordonnées : {item['coordinates']}")
            question_text = self.extract_text(image, item["coordinates"])
            print(f"Texte de la question extrait : {question_text}")
            responses = []
            max_pixels = 150  # Seuil minimum pour considérer une case cochée
            selected_label = None

            for case in item["cases"]:
                case_coords = case["cases_coordinates"]
                label_coords = case["label_coordinates"]

                num_pixels = self.get_checked_pixels(image, case_coords)
                print(f"Nombre de pixels cochés pour la case avec les coordonnées {case_coords} : {num_pixels}")
                if num_pixels > max_pixels:
                    max_pixels = num_pixels
                    selected_label = self.extract_text(image, label_coords)
                    print(f"Case sélectionnée avec le label : {selected_label}")

            if selected_label:
                responses.append(selected_label)

            results.append({
                "question": question_text,
                "responses": responses
            })

        return results

    def extract_text(self, image, coords):
        x, y, w, h = int(coords["start_x"]), int(coords["start_y"]), int(coords["end_x"] - coords["start_x"]), int(coords["end_y"] - coords["start_y"])
        roi = image[y:y+h, x:x+w]
        text = pytesseract.image_to_string(roi, config='--psm 6')
        print(f"Extraction de texte dans la région avec les coordonnées {coords} : {text.strip()}")
        return text.strip()

    def get_checked_pixels(self, image, coords):
        x, y, w, h = int(coords["start_x"]), int(coords["start_y"]), int(coords["end_x"] - coords["start_x"]), int(coords["end_y"] - coords["start_y"])
        roi = image[y:y+h, x:x+w]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        return cv2.countNonZero(thresh)

    def display_results(self, results):
        result_window = tk.Toplevel(self.root)
        result_window.title("Résultats de l'analyse")
        result_text = tk.Text(result_window, wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True)

        for result in results:
            result_text.insert(tk.END, f"Results for {result['image']}:\n")
            for analysis in result['analysis']:
                result_text.insert(tk.END, f"  Question: {analysis['question']}\n")
                for response in analysis['responses']:
                    result_text.insert(tk.END, f"    Response: {response}\n")
            result_text.insert(tk.END, "\n")

        result_text.config(state=tk.DISABLED)

    def export_to_excel(self):
        if not self.results:
            messagebox.showerror("Erreur", "Aucun résultat à exporter. Veuillez d'abord effectuer l'analyse.")
            return

        # Extraire les questions pour la première ligne
        questions = []
        for result in self.results:
            for analysis in result['analysis']:
                question = analysis['question']
                if question not in questions:
                    questions.append(question)

        # Créer une liste de dictionnaires pour les données à exporter
        data = []
        for result in self.results:
            row = {'Image': result['image']}
            for analysis in result['analysis']:
                question = analysis['question']
                response = analysis['responses'][0] if analysis['responses'] else ""
                row[question] = response
            data.append(row)

        # Convertir en DataFrame pandas
        df = pd.DataFrame(data, columns=['Image'] + questions)

        # Ouvrir le dialogue pour enregistrer le fichier Excel
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Succès", "Les résultats ont été exportés vers Excel avec succès.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CanvasApp(root)
    root.mainloop()