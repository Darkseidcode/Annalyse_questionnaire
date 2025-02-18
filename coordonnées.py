import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import json

class ZoneEnregistreur:
    def __init__(self, root):
        self.root = root
        self.root.title("Enregistreur de Zones")
        
        # Frame pour le canvas
        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Canvas avec scrollbar
        canvas_frame = tk.Frame(self.frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, width=800, height=600, scrollregion=(0, 0, 2000, 2000))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=self.scrollbar.set)
        
        # Crée une liste pour stocker les questions
        self.questions = []

        # Variables globales pour stocker les coordonnées de départ et le rectangle actuel
        self.start_x, self.start_y = None, None
        self.current_rect = None

        # Initialiser les compteurs de questions et de cases
        self.question_counter = 1

        # Initialiser le mode (question, case ou label)
        self.mode = "question"

        # Ajouter un bouton pour passer à la question suivante
        button_frame = tk.Frame(root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.next_question_button = tk.Button(button_frame, text="Mode: Question (Cliquez pour cases)", command=self.next_question)
        self.next_question_button.pack(fill=tk.X, pady=2)

        self.load_button = tk.Button(button_frame, text="Charger l'image", command=self.load_image_dialog)
        self.load_button.pack(fill=tk.X, pady=2)

        # Lier les événements de souris aux fonctions correspondantes
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def save_zones_to_json(self):
        with open("questions.json", "w") as file:
            json.dump(self.questions, file, indent=4)

    def on_click(self, event):
        self.start_x, self.start_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.display_coordinates(self.start_x, self.start_y)
        # Définir la couleur en fonction du mode
        if self.mode == "question":
            color = 'green'
        elif self.mode == "case":
            color = 'blue'
        else:  # mode == "label"
            color = 'purple'
        self.current_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=color)

    def on_drag(self, event):
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def on_release(self, event):
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.display_coordinates(end_x, end_y)
        if self.mode == "question":
            # Générer automatiquement le nom de la question avec une numérotation
            question = f"Question {self.question_counter}"
            self.question_counter += 1
            # Ajouter la question à la liste des questions
            self.questions.append({"question": question, "coordinates": {"start_x": self.start_x, "start_y": self.start_y, "end_x": end_x, "end_y": end_y}, "cases": []})
            print(f"Question enregistrée: {question} avec coordonnées start_x={self.start_x}, start_y={self.start_y}, end_x={end_x}, end_y={end_y}")
            # Passer automatiquement en mode case après avoir ajouté une question
            self.mode = "case"
        elif self.mode == "case":
            # Ajouter la zone de détection de cases à la dernière question
            if self.questions:
                current_case = {"cases_coordinates": {"start_x": self.start_x, "start_y": self.start_y, "end_x": end_x, "end_y": end_y}, "label_coordinates": {}}
                self.questions[-1]["cases"].append(current_case)
                print(f"Zone de cases ajoutée à la question {self.questions[-1]['question']} avec coordonnées start_x={self.start_x}, start_y={self.start_y}, end_x={end_x}, end_y={end_y}")
                # Passer automatiquement en mode label après avoir ajouté une zone de cases
                self.mode = "label"
            else:
                messagebox.showerror("Erreur", "Aucune question disponible pour ajouter une zone de cases.")
        elif self.mode == "label":
            # Ajouter la zone de détection de texte (label) à la dernière case de la dernière question
            if self.questions and self.questions[-1]["cases"]:
                self.questions[-1]["cases"][-1]["label_coordinates"] = {"start_x": self.start_x, "start_y": self.start_y, "end_x": end_x, "end_y": end_y}
                print(f"Label ajouté à la case avec coordonnées start_x={self.start_x}, start_y={self.start_y}, end_x={end_x}, end_y={end_y}")
                # Passer automatiquement en mode case après avoir ajouté un label
                self.mode = "case"
            else:
                messagebox.showerror("Erreur", "Aucune case disponible pour ajouter un label.")
        self.save_zones_to_json()
        # Réinitialiser les variables de départ
        self.start_x, self.start_y = None, None
        # Mettre à jour le texte du bouton en fonction du mode
        self.update_mode_button_text()

    def display_coordinates(self, x, y):
        print(f"Coordonnées: x={x}, y={y}")
        if self.img:
            img_width, img_height = self.img.size
            if 0 <= x < img_width and 0 <= y < img_height:
                print("Les coordonnées sont dans les limites de l'image.")
            else:
                print("Les coordonnées ne sont pas dans les limites de l'image.")

    def next_question(self):
        self.mode = "question"
        self.update_mode_button_text()

    def update_mode_button_text(self):
        if self.mode == "question":
            self.next_question_button.config(text="Mode: Question")
        elif self.mode == "case":
            self.next_question_button.config(text="Mode: Case")
        else:  # mode == "label"
            self.next_question_button.config(text="Mode: Label")

    def load_image_dialog(self):
        file_path = filedialog.askopenfilename(title="Choisir une image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.load_image(file_path)

    def load_image(self, path):
        self.img = Image.open(path)
        self.img_tk = ImageTk.PhotoImage(self.img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        # Ajuster la région de défilement pour s'adapter à la taille de l'image
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

if __name__ == "__main__":
    root = tk.Tk()
    app = ZoneEnregistreur(root)
    root.mainloop()