import flet as ft
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import tempfile
import os
import sys
import json

# ===== UTILITAIRE POUR GÉRER LES ASSETS =====
def get_asset_path(relative_path):
    """
    Retourne le chemin correct vers un asset, que ce soit en développement ou en exécutable.
    
    Args:
        relative_path (str): Chemin relatif depuis le dossier assets (ex: "icon.png", "images/logo.jpg")
    
    Returns:
        str: Chemin complet vers l'asset
    """
    try:
        # PyInstaller stocke les fichiers temporaires dans _MEIPASS
        base_path = sys._MEIPASS
        asset_path = os.path.join(base_path, 'assets', relative_path)
        
        if os.path.exists(asset_path):
            return asset_path
            
    except AttributeError:
        # Nous sommes en mode développement
        pass
    
    # Chemins pour le mode développement
    dev_paths = [
        os.path.join('src', 'assets', relative_path),
        os.path.join('assets', relative_path),
        os.path.join('.', 'src', 'assets', relative_path),
        os.path.join('.', 'assets', relative_path)
    ]
    
    for path in dev_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    # Si aucun chemin n'est trouvé, retourner le chemin par défaut
    print(f"Warning: Asset '{relative_path}' non trouvé")
    return relative_path

def list_available_assets():
    """Liste tous les assets disponibles pour debug"""
    try:
        # En mode exécutable
        base_path = sys._MEIPASS
        assets_path = os.path.join(base_path, 'assets')
        if os.path.exists(assets_path):
            print("Assets disponibles dans l'exécutable :")
            for root, dirs, files in os.walk(assets_path):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), assets_path)
                    print(f"  - {rel_path}")
    except AttributeError:
        # En mode développement
        dev_assets_paths = ['src/assets', 'assets']
        for assets_path in dev_assets_paths:
            if os.path.exists(assets_path):
                print(f"Assets disponibles en développement ({assets_path}) :")
                for root, dirs, files in os.walk(assets_path):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), assets_path)
                        print(f"  - {rel_path}")
                break

# ===== CLASSES PRINCIPALES =====

class DatabaseManager:
    def __init__(self, db_path="projet_estimation.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec toutes les tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table principale des projets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                description TEXT,
                categories TEXT,
                date_creation DATE DEFAULT CURRENT_DATE,
                statut TEXT DEFAULT 'En cours'
            )
        """)
        
        # Tables pour chaque catégorie de coûts
        tables = [
            "logistique_transport",
            "materiel_electrique", 
            "materiel_genie_civil",
            "materiel_instrumentation",
            "ingenieur_process",
            "materiel_tuyauterie",
            "main_oeuvre_electric",
            "main_oeuvre_installation",
            "main_oeuvre_tuyauterie"
        ]
        
        for table in tables:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    projet_id INTEGER,
                    description TEXT NOT NULL,
                    quantite REAL DEFAULT 1,
                    prix_unitaire REAL NOT NULL,
                    cout_total REAL GENERATED ALWAYS AS (quantite * prix_unitaire) STORED,
                    FOREIGN KEY (projet_id) REFERENCES projets (id) ON DELETE CASCADE
                )
            """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def create_project(self, nom: str, description: str = "", categories: str = ""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projets (nom, description, categories) VALUES (?, ?, ?)", (nom, description, categories))
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id
    
    def get_projects(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, description, date_creation, statut FROM projets")
        projects = cursor.fetchall()
        conn.close()
        return projects
    
    def delete_project(self, project_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projets WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()
    
    def add_item(self, table_name: str, projet_id: int, description: str, quantite: float, prix_unitaire: float):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {table_name} (projet_id, description, quantite, prix_unitaire) 
            VALUES (?, ?, ?, ?)
        """, (projet_id, description, quantite, prix_unitaire))
        conn.commit()
        conn.close()
    
    def get_items(self, table_name: str, projet_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, description, quantite, prix_unitaire, cout_total FROM {table_name} WHERE projet_id = ?", (projet_id,))
        items = cursor.fetchall()
        conn.close()
        return items
    
    def delete_item(self, table_name: str, item_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
    
    def get_project_total_cost(self, projet_id: int):
        tables = [
            "logistique_transport", "materiel_electrique", "materiel_genie_civil",
            "materiel_instrumentation", "ingenieur_process", "materiel_tuyauterie",
            "main_oeuvre_electric", "main_oeuvre_installation", "main_oeuvre_tuyauterie"
        ]
        
        conn = self.get_connection()
        cursor = conn.cursor()
        total_cost = 0
        category_costs = {}
        
        for table in tables:
            cursor.execute(f"SELECT SUM(cout_total) FROM {table} WHERE projet_id = ?", (projet_id,))
            result = cursor.fetchone()
            cost = result[0] if result[0] else 0
            category_costs[table] = cost
            total_cost += cost
        
        conn.close()
        return total_cost, category_costs
    
    def create_category_template_table(self, category_key):
        """Créer une table template pour une catégorie"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        table_name = f"{category_key}_templates"
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                prix_unitaire REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    def add_template_item(self, category_key: str, description: str, prix_unitaire: float):
        """Ajouter un élément template"""
        table_name = f"{category_key}_templates"
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {table_name} (description, prix_unitaire) 
            VALUES (?, ?)
        """, (description, prix_unitaire))
        conn.commit()
        conn.close()

    def get_template_items(self, category_key: str):
        """Récupérer les éléments template d'une catégorie"""
        table_name = f"{category_key}_templates"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT id, description, prix_unitaire FROM {table_name}")
            items = cursor.fetchall()
        except:
            items = []
        conn.close()
        return items

    def delete_template_item(self, category_name: str, item_id: int):
        """Supprimer un élément template"""
        table_name = f"{category_name}_templates"
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def get_project_details(self, projet_id: int):
        """Récupérer tous les détails d'un projet pour l'export"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Informations du projet
        cursor.execute("SELECT nom, description, date_creation FROM projets WHERE id = ?", (projet_id,))
        project_info = cursor.fetchone()
        
        # Détails par catégorie
        tables = [
            "logistique_transport", "materiel_electrique", "materiel_genie_civil",
            "materiel_instrumentation", "ingenieur_process", "materiel_tuyauterie",
            "main_oeuvre_electric", "main_oeuvre_installation", "main_oeuvre_tuyauterie"
        ]
        
        details = {}
        for table in tables:
            cursor.execute(f"""
                SELECT description, quantite, prix_unitaire, cout_total 
                FROM {table} WHERE projet_id = ? ORDER BY description
            """, (projet_id,))
            details[table] = cursor.fetchall()
        
        conn.close()
        return project_info, details

class PDFExporter:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def create_logo_image(self, img_path, max_width=50, max_height=50):
        """Créer un objet Image optimisé pour le tableau"""
        try:
            if os.path.exists(img_path):
                # Créer l'objet Image avec les dimensions souhaitées
                logo = Image(img_path)
                
                # Obtenir les dimensions originales
                original_width, original_height = logo.imageWidth, logo.imageHeight
                
                # Calculer le ratio pour maintenir les proportions
                width_ratio = max_width / original_width
                height_ratio = max_height / original_height
                ratio = min(width_ratio, height_ratio)
                
                # Définir les nouvelles dimensions
                new_width = original_width * ratio
                new_height = original_height * ratio
                
                logo.drawWidth = new_width
                logo.drawHeight = new_height
                
                return logo
            else:
                # Si le logo n'existe pas, retourner un texte de remplacement
                return Paragraph("LOGO", ParagraphStyle('LogoStyle', 
                                                       fontSize=12, 
                                                       fontName='Helvetica-Bold',
                                                       alignment=1))
        except Exception as e:
            print(f"Erreur lors du chargement du logo: {e}")
            return Paragraph("LOGO", ParagraphStyle('LogoStyle', 
                                                   fontSize=12, 
                                                   fontName='Helvetica-Bold',
                                                   alignment=1))
        
    def export_project_to_pdf(self, project_id: int, filename: str = None):
        """Exporter un projet en PDF avec style Excel professionnel"""
        if not filename:
            filename = f"estimation_projet_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Récupérer les données
        project_info, details = self.db.get_project_details(project_id)
        total_cost, category_costs = self.db.get_project_total_cost(project_id)
        
        if not project_info:
            raise ValueError("Projet introuvable")
        
        # Récupérer les catégories du projet
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT categories FROM projets WHERE id = ?", (project_id,))
        result = cursor.fetchone()
        conn.close()
        
        project_categories = result[0].split(',') if result[0] else []
        
        # Créer le document PDF
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                              topMargin=0.5*inch, bottomMargin=0.5*inch,
                              leftMargin=0.5*inch, rightMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Style personnalisé pour l'en-tête
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,  # Center
            spaceAfter=5,
            fontName='Helvetica-Bold'
        )

        header_style_left = ParagraphStyle(
            'CustomHeaderLeft',
            parent=styles['Normal'],
            fontSize=9,
            alignment=0,  # Left
            spaceBefore=2,
            fontName='Helvetica'
        )

        header_style_right = ParagraphStyle(
            'CustomHeaderRight',
            parent=styles['Normal'],
            fontSize=9,
            alignment=2,  # Right
            spaceBefore=2,
            fontName='Helvetica'
        )
        
        # Style pour les titres de sections
        section_style = ParagraphStyle(
            'SectionStyle',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            spaceAfter=3,
            spaceBefore=3
        )
        
        # CORRECTION : Utiliser get_asset_path pour trouver le logo
        logo_path = get_asset_path("icon.png")  # ou le nom de votre fichier logo
        
        # Vérifier si le logo existe
        logo_exists = os.path.exists(logo_path) if logo_path else False
        
        # === EN-TÊTE AVEC LOGO ET INFOS ENTREPRISE ===
        
        # Créer le logo ou un placeholder
        if logo_exists:
            logo_element = self.create_logo_image(logo_path, max_width=60, max_height=50)
        else:
            logo_element = Paragraph("PROSEEN<br/>LOGO", ParagraphStyle(
                'LogoPlaceholder',
                fontSize=8,
                fontName='Helvetica-Bold',
                alignment=1,
                textColor=colors.blue
            ))
        
        # Données de l'en-tête
        header_data = [
            # Ligne 1: Logo + Titre central + Logo client
            [
                logo_element,
                Paragraph("ETUDES APD POUR LA CONSTRUCTION D'UNE INFRASTRUCTURE<br/>" + 
                         f"<b>{project_info[0].upper()}</b>", header_style),
                Paragraph("CLIENT<br/><i>(Logo Client)</i>", header_style)
            ],
            # Ligne 2: Infos entreprise + vide + référence
            [
                Paragraph("PROSEEN<br/>Abidjan, Côte d'Ivoire<br/>Tél: +225 XX XX XX XX<br/>Email: contact@proseen.ci", 
                         header_style_left),
                "",
                Paragraph(f"REF: PROJ-{project_id:03d}<br/>DATE: {datetime.now().strftime('%d/%m/%Y')}<br/>Version: 1.0", 
                         header_style_right)
            ]
        ]
        
        # Configuration du tableau d'en-tête
        header_table = Table(header_data, colWidths=[2.5*inch, 3*inch, 2.5*inch], rowHeights=[70, 50])
        header_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Logo centré
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Titre centré
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),  # Client centré
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 0), (-1, 0), [colors.lightgrey]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
        
        # === SECTION DEMANDE D'ÉTUDE ===
        demande_data = [
            ["DEMANDE D'ÉTUDE :", "", "OBJET:", project_info[0]],
        ]
        
        demande_table = Table(demande_data, colWidths=[1.5*inch, 1*inch, 1*inch, 4.5*inch])
        demande_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('BACKGROUND', (2, 0), (2, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(demande_table)
        story.append(Spacer(1, 15))
        
        # === TABLEAU PRINCIPAL DES ESTIMATIONS ===
        # En-tête du tableau principal
        main_header_data = [
            ["DÉSIGNATION","QTÉ", "P.U (FCFA)", "P.T (FCFA)", "OBSERVATIONS"],
            ["(1)","(2)", "(3)", "(4)", "(5)"]
        ]
        
        main_table_data = []
        main_table_data.extend(main_header_data)
        
        # Ajouter les données par catégorie
        categories_display = {
            "logistique_transport": "LOGISTIQUE & TRANSPORT",
            "materiel_electrique": "APPAREILS ÉLECTRIQUES", 
            "materiel_genie_civil": "MATÉRIEL GÉNIE CIVIL",
            "materiel_instrumentation": "MATÉRIEL INSTRUMENTATION",
            "ingenieur_process": "INGÉNIEUR PROCESS",
            "materiel_tuyauterie": "MATÉRIEL TUYAUTERIE",
            "main_oeuvre_electric": "MAIN D'ŒUVRE ÉLECTRIQUE",
            "main_oeuvre_installation": "MAIN D'ŒUVRE INSTALLATION", 
            "main_oeuvre_tuyauterie": "MAIN D'ŒUVRE TUYAUTERIE"
        }
        
        for cat_key in project_categories:
            if cat_key in details and details[cat_key]:
                # Ligne de titre de catégorie
                cat_title = categories_display.get(cat_key, cat_key.upper())
                main_table_data.append([cat_title, "", "", "", ""])
                
                # Items de la catégorie
                for item in details[cat_key]:
                    description = item[0][:45] + "..." if len(item[0]) > 45 else item[0]
                    main_table_data.append([
                        description,  # DÉSIGNATION
                        f"{item[1]}", # QTÉ
                        f"{item[2]:,.0f}", # P.U
                        f"{item[3]:,.0f}", # P.T
                        ""           # OBSERVATIONS
                    ])
        
        # Ligne de total
        main_table_data.append([
            "TOTAL GÉNÉRAL", "", "", f"{total_cost:,.0f}", ""
        ])
        
        # Créer le tableau principal
        main_table = Table(main_table_data, colWidths=[
            2.8*inch,  # DÉSIGNATION
            0.8*inch,  # QTÉ
            1.2*inch,  # P.U
            1.2*inch,  # P.T
            2*inch     # OBSERVATIONS
        ])
        
        # Style du tableau principal
        table_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            
            # En-tête principal
            ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            
            # Ligne de total
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
        ]
        
        # Ajouter les styles pour les titres de catégories
        row_index = 2  # Commencer après l'en-tête
        for cat_key in project_categories:
            if cat_key in details and details[cat_key]:
                table_style.append(('BACKGROUND', (0, row_index), (-1, row_index), colors.grey))
                table_style.append(('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold'))
                table_style.append(('SPAN', (0, row_index), (-1, row_index)))
                table_style.append(('FONTSIZE', (0, row_index), (-1, row_index), 9))
                row_index += 1 + len(details[cat_key])  # +1 pour le titre, + nombre d'items
        
        main_table.setStyle(TableStyle(table_style))
        story.append(main_table)
        
        # Ajouter une note en bas de page
        story.append(Spacer(1, 20))
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Oblique',
            textColor=colors.grey,
            alignment=1
        )
        
        # Générer le PDF
        doc.build(story)
        return filename

# Le reste du code (CostEstimationApp, BDApp, WelcomePage) reste identique
# mais il faut ajouter la configuration de l'icône de la fenêtre dans main()

class CostEstimationApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.pdf_exporter = PDFExporter(self.db)
        self.page = None
        self.current_project = None
        self.file_picker = None
        
        # Configuration des catégories
        self.categories = {
            "logistique_transport": "Logistique & Transport",
            "materiel_electrique": "Matériel Électrique",
            "materiel_genie_civil": "Matériel Génie Civil", 
            "materiel_instrumentation": "Matériel Instrumentation",
            "ingenieur_process": "Ingénieur Process",
            "materiel_tuyauterie": "Matériel Tuyauterie",
            "main_oeuvre_electric": "Main d'œuvre Électrique",
            "main_oeuvre_installation": "Main d'œuvre Installation",
            "main_oeuvre_tuyauterie": "Main d'œuvre Tuyauterie"
        }
        
        # Initialize template tables for all categories
        for category_key in self.categories.keys():
            self.db.create_category_template_table(category_key)
    
    def main(self, page: ft.Page):
        """Initialiser la page principale de l'application"""
        self.page = page
        page.title = "Estimation des Coûts de Projets"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1200
        page.window_height = 800
        page.padding = 0
        logo_path = get_asset_path("icon.ico")
        page.window_icon = logo_path
        
        # CORRECTION : Configuration de l'icône de la fenêtre
        icon_path = get_asset_path("icon.ico")  # ou le nom de votre fichier icône
        if os.path.exists(icon_path):
            page.window.icon = icon_path
        
        self.file_picker = ft.FilePicker(on_result=self.save_pdf_dialog_result)
        page.overlay.append(self.file_picker)
        
        # Navigation rail
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME,
                    selected_icon=ft.Icons.HOME,
                    label="Accueil"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ADD,
                    selected_icon=ft.Icons.ADD,
                    label="Nouveau Projet"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CALCULATE,
                    selected_icon=ft.Icons.CALCULATE,
                    label="Estimation"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.BAR_CHART,
                    selected_icon=ft.Icons.BAR_CHART,
                    label="Graphiques"
                ),
            ],
            on_change=self.nav_changed
        )
        
        self.nav_rail.selected_index = 0
        self.nav_rail.on_change = self.nav_changed

        # Container principal pour le contenu
        self.content_area = ft.Container(
            expand=True,
            padding=20,
        )
        
        page.appbar = ft.AppBar(
            leading_width=50,
            title=ft.Text("Estimation des Coûts de Projets", size=30, weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.Colors.BLUE_100,
            actions=[
                ft.IconButton(ft.Icons.INFO,
                    tooltip="À propos",
                    on_click=lambda e: self.show_snack_bar("Application de gestion des coûts de projets", ft.Colors.BLUE_700)),
                ft.IconButton(ft.Icons.HOME,
                    tooltip="Page d'accueil",
                    on_click=self.go_to_accueil),
            ]
        )

        # Layout principal
        page.controls.clear()
        page.add(
            ft.Row([
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area
            ], expand=True, alignment=ft.MainAxisAlignment.START
        ))
        
        # Charger la page d'accueil
        self.show_home_page()
    
    # Toutes les autres méthodes de CostEstimationApp restent identiques...
    # [Le reste du code reste inchangé car il ne concerne pas directement les assets]
    
    def show_new_project_page(self):
        """Page de création de nouveau projet avec sélection de catégories"""
        self.project_name_field = ft.TextField(
            label="Nom du projet",
            hint_text="Entrez le nom du projet",
            width=400
        )
        
        self.project_desc_field = ft.TextField(
            label="Description",
            hint_text="Description du projet (optionnel)",
            width=400,
            multiline=True,
            max_lines=3
        )

        # Créer les checkboxes pour les catégories
        self.category_checkboxes = {}
        category_widgets = []
        
        for key, name in self.categories.items():
            checkbox = ft.Checkbox(label=name, value=True)  # Toutes cochées par défaut
            self.category_checkboxes[key] = checkbox
            category_widgets.append(checkbox)
        
        content = ft.Column([
            ft.Text("Nouveau Projet", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Container(height=20),
            self.project_name_field,
            self.project_desc_field,
            ft.Container(height=20),
            ft.Text("Sélectionner les catégories à inclure:", size=16, weight=ft.FontWeight.BOLD),
            ft.Column([
                ft.Row(category_widgets[:3]),  # 3 par ligne
                ft.Row(category_widgets[3:6]),
                ft.Row(category_widgets[6:9])
            ]),
            ft.Container(height=20),
            ft.Row([
                ft.ElevatedButton(
                    "Créer le projet",
                    icon=ft.Icons.CREATE,
                    on_click=self.create_project
                ),
                ft.OutlinedButton(
                    "Annuler",
                    on_click=self.go_to_home
                )
            ])
        ])
        
        self.content_area.content = content
        self.page.update()
    
    def create_project(self, e):
        """Créer un nouveau projet avec les catégories sélectionnées"""
        if not self.project_name_field.value:
            self.show_snack_bar("Le nom du projet est requis", ft.Colors.RED)
            return
        
        # Récupérer les catégories sélectionnées
        selected_categories = []
        for key, checkbox in self.category_checkboxes.items():
            if checkbox.value:
                selected_categories.append(key)
        
        if not selected_categories:
            self.show_snack_bar("Sélectionnez au moins une catégorie", ft.Colors.RED)
            return
        
        try:
            project_id = self.db.create_project(
                self.project_name_field.value,
                self.project_desc_field.value or "",
                categories=",".join(selected_categories)
            )
            self.show_snack_bar("Projet créé avec succès!", ft.Colors.GREEN)
            self.show_home_page()
        except Exception as ex:
            self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
    
    def show_project_categories(self):
        """Afficher uniquement les catégories sélectionnées pour le projet"""
        if not self.current_project:
            return
        
        project_id, project_name = self.current_project[0], self.current_project[1]
        
        # Récupérer les catégories du projet
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT categories FROM projets WHERE id = ?", (project_id,))
        result = cursor.fetchone()
        conn.close()
        
        project_categories = result[0].split(',') if result[0] else []
        
        total_cost, category_costs = self.db.get_project_total_cost(project_id)
        
        category_cards = []
        for cat_key in project_categories:
            if cat_key in self.categories:
                cat_name = self.categories[cat_key]
                cost = category_costs.get(cat_key, 0)
                items_count = len(self.db.get_items(cat_key, project_id))
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.CATEGORY),
                                title=ft.Text(cat_name, weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"{items_count} éléments | {cost} FCFA"),
                            ),
                            ft.ElevatedButton(
                                "Gérer",
                                icon=ft.Icons.SETTINGS,
                                on_click=lambda e, cat=cat_key: self.manage_category(cat)
                            )
                        ]),
                        padding=10
                    ),
                    width=300
                )
                category_cards.append(card)
        
        content = ft.Column([
            ft.Row([
                ft.Text(f"Projet: {project_name}", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Coût Total: {total_cost} FCFA", size=18, color=ft.Colors.GREEN)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.GridView(
                category_cards,
                runs_count=3,
                max_extent=300,
                child_aspect_ratio=1.2,
                spacing=10,
                run_spacing=10,
            ) if category_cards else ft.Text("Aucune catégorie sélectionnée pour ce projet"),
            ft.Container(height=20),
            ft.ElevatedButton(
                "Retour aux projets",
                icon=ft.Icons.ARROW_BACK,
                on_click=self.go_to_home
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.content_area.content = content
        self.page.update()
    
    def manage_category(self, category_key):
        """Gérer les éléments d'une catégorie avec sélection depuis la BD"""
        if not self.current_project:
            return
        
        project_id = self.current_project[0]
        category_name = self.categories[category_key]
        
        # Récupérer les éléments du projet pour cette catégorie
        project_items = self.db.get_items(category_key, project_id)
        
        # Récupérer les éléments templates de la BD
        template_items = self.db.get_template_items(category_key)
        
        # Formulaire d'ajout manuel
        desc_field = ft.TextField(label="Description", width=300)
        qty_field = ft.TextField(label="Quantité", value="1", width=100)
        price_field = ft.TextField(label="Prix unitaire (FCFA)", width=150)
        
        def add_manual_item_handler(e):
            if not all([desc_field.value, qty_field.value, price_field.value]):
                self.show_snack_bar("Tous les champs sont requis", ft.Colors.RED)
                return
            
            try:
                self.db.add_item(
                    category_key,
                    project_id,
                    desc_field.value,
                    float(qty_field.value),
                    float(price_field.value)
                )
                desc_field.value = ""
                qty_field.value = "1"
                price_field.value = ""
                self.show_snack_bar("Élément ajouté", ft.Colors.GREEN)
                self.manage_category(category_key)  # Refresh
            except ValueError:
                self.show_snack_bar("Quantité et prix doivent être numériques", ft.Colors.RED)
            except Exception as ex:
                self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
        
        # Section sélection depuis la BD
        template_dropdown = ft.Dropdown(
            label="Sélectionner depuis la BD",
            options=[
                ft.dropdown.Option(str(i), f"{item[1]} - {item[2]} FCFA") 
                for i, item in enumerate(template_items)
            ],
            width=400
        ) if template_items else ft.Text("Aucun élément template disponible")
        
        template_qty_field = ft.TextField(label="Quantité", value="1", width=100)
        
        def add_from_template_handler(e):
            if not template_dropdown.value or not template_qty_field.value:
                self.show_snack_bar("Sélectionnez un élément et spécifiez la quantité", ft.Colors.RED)
                return
            
            try:
                template_index = int(template_dropdown.value)
                template_item = template_items[template_index]
                
                self.db.add_item(
                    category_key,
                    project_id,
                    template_item[1],  # description
                    float(template_qty_field.value),
                    template_item[2]   # prix_unitaire
                )
                
                template_dropdown.value = None
                template_qty_field.value = "1"
                self.show_snack_bar("Élément ajouté depuis la BD", ft.Colors.GREEN)
                self.manage_category(category_key)  # Refresh
            except (ValueError, IndexError):
                self.show_snack_bar("Erreur dans la sélection", ft.Colors.RED)
            except Exception as ex:
                self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
        
        # Liste des éléments du projet
        items_list = []
        total_category_cost = 0
        
        for item in project_items:
            total_category_cost += item[4]  # cout_total
            
            def delete_item_handler(e, item_id=item[0]):
                self.delete_item(category_key, item_id)
            
            item_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item[1])),  # description
                    ft.DataCell(ft.Text(str(item[2]))),  # quantite
                    ft.DataCell(ft.Text(f"{item[3]}")),  # prix_unitaire
                    ft.DataCell(ft.Text(f"{item[4]}")),  # cout_total
                    ft.DataCell(
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            on_click=delete_item_handler
                        )
                    ),
                ]
            )
            items_list.append(item_row)
        
        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Description")),
                ft.DataColumn(ft.Text("Quantité")),
                ft.DataColumn(ft.Text("Prix unitaire")),
                ft.DataColumn(ft.Text("Coût total")),
                ft.DataColumn(ft.Text("Action")),
            ],
            rows=items_list,
        ) if items_list else ft.Text("Aucun élément ajouté")
        
        content = ft.Column([
            ft.Text(f"{category_name} - {self.current_project[1]}", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Coût total catégorie: {total_category_cost} FCFA", size=16, color=ft.Colors.BLUE),
            ft.Divider(),
            
            # Section ajout depuis la BD
            ft.Container(
                content=ft.Column([
                    ft.Text("Ajouter depuis la Base de Données:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                    ft.Row([template_dropdown, template_qty_field]) if template_items else ft.Text("Aucun template disponible"),
                    ft.ElevatedButton(
                        "Ajouter depuis BD", 
                        icon=ft.Icons.DATA_ARRAY, 
                        on_click=add_from_template_handler,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
                    ) if template_items else ft.Container()
                ]),
                bgcolor=ft.Colors.BLUE_50,
                padding=15,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.BLUE_200)
            ),
            
            ft.Container(height=20),
            
            # Section ajout manuel
            ft.Container(
                content=ft.Column([
                    ft.Text("Ajouter manuellement:", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                    ft.Row([desc_field, qty_field, price_field]),
                    ft.ElevatedButton(
                        "Ajouter manuellement", 
                        icon=ft.Icons.ADD, 
                        on_click=add_manual_item_handler,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE)
                    )
                ]),
                bgcolor=ft.Colors.GREEN_50,
                padding=15,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.GREEN_200)
            ),
            
            ft.Container(height=20),
            ft.Text("Éléments du projet:", weight=ft.FontWeight.BOLD),
            data_table,
            
            ft.Container(height=20),
            ft.ElevatedButton(
                "Retour aux catégories",
                icon=ft.Icons.ARROW_BACK,
                on_click=self.go_to_categories
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.content_area.content = content
        self.page.update()
    
    def nav_changed(self, e):
        selected = e.control.selected_index
        if selected == 0:
            self.show_home_page()
        elif selected == 1:
            self.show_new_project_page()
        elif selected == 2:
            self.show_estimation_page()
        elif selected == 3:
            self.show_charts_page()
        self.page.update()
    
    def show_home_page(self):
        """Page d'accueil avec liste des projets"""
        projects = self.db.get_projects()
        
        project_cards = []
        for project in projects:
            total_cost, _ = self.db.get_project_total_cost(project[0])
            
            def edit_project_handler(e, p=project):
                self.edit_project(p)
            
            def export_pdf_handler(e, p=project):
                self.export_project_pdf(p)
            
            def delete_project_handler(e, p=project):
                self.delete_project_confirm(p)
            
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.FOLDER),
                            title=ft.Text(project[1], weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Créé le: {project[3]} | Coût total: {total_cost} FCFA"),
                        ),
                        ft.Row([
                            ft.ElevatedButton(
                                "Modifier",
                                icon=ft.Icons.EDIT,
                                on_click=edit_project_handler
                            ),
                            ft.ElevatedButton(
                                "Export PDF",
                                icon=ft.Icons.PICTURE_AS_PDF,
                                color=ft.Colors.BLUE,
                                on_click=export_pdf_handler
                            ),
                            
                        ], alignment=ft.MainAxisAlignment.CENTER),

                        ft.Row([
                            ft.ElevatedButton(
                                "Supprimer",
                                icon=ft.Icons.DELETE,
                                color=ft.Colors.RED,
                                on_click=delete_project_handler
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                    ]),
                    padding=10,
                    height=150,
                    width=300,
                ),
            )
            project_cards.append(card)
        
        if not project_cards:
            def create_new_project_handler(e):
                self.nav_rail.selected_index = 1
                self.show_new_project_page()
                self.page.update()
            
            content = ft.Column([
                ft.Text("Aucun projet trouvé", size=20, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(
                    "Créer un nouveau projet",
                    icon=ft.Icons.ADD,
                    on_click=create_new_project_handler
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            content = ft.Column([
                ft.Text("Les Projets", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.GridView(
                    project_cards,
                    runs_count=3,
                    max_extent=400,
                    child_aspect_ratio=1.5,
                    spacing=10,
                    run_spacing=10,
                )
            ])
        
        self.content_area.content = content
        self.page.update()
    
    def go_to_home(self, e=None):
        """Aller à la page d'accueil"""
        self.nav_rail.selected_index = 0
        self.show_home_page()
        self.page.update()
    
    def go_to_accueil(self, e=None):
        """Retourner à la page d'accueil principale"""
        self.page.controls.clear()
        self.page.appbar = None     # Remove appbar
        welcome_page = WelcomePage(self.page)
        welcome_content = welcome_page.create_welcome_content()
        self.page.add(welcome_content)
        self.page.update()
    
    def edit_project(self, project):
        """Modifier un projet - afficher les catégories"""
        self.current_project = project
        self.show_project_categories()
    
    def export_project_pdf(self, project):
        """Exporter un projet en PDF"""
        self.current_project = project
        # Ouvrir le dialogue "Enregistrer sous"
        self.file_picker.save_file(
            allowed_extensions=["pdf"],
            file_name=f"estimation_projet_{project[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
    
    def save_pdf_dialog_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            try:
                filename = self.pdf_exporter.export_project_to_pdf(self.current_project[0], filename=e.path)
                self.show_snack_bar(f"PDF exporté : {filename}", ft.Colors.GREEN)
            except Exception as ex:
                self.show_snack_bar(f"Erreur lors de l'export PDF: {str(ex)}", ft.Colors.RED)
        else:
            self.show_snack_bar("Export annulé", ft.Colors.RED)
 
    def show_charts_page(self):
        """Page des graphiques de répartition des coûts"""
        projects = self.db.get_projects()
        
        if not projects:
            def create_new_project_handler(e):
                self.nav_rail.selected_index = 1
                self.show_new_project_page()
                self.page.update()
                
            content = ft.Column([
                ft.Text("Aucun projet pour les graphiques", size=20),
                ft.ElevatedButton(
                    "Créer un projet",
                    on_click=create_new_project_handler
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            # Dropdown pour sélectionner un projet
            project_dropdown = ft.Dropdown(
                label="Sélectionner un projet",
                options=[ft.dropdown.Option(str(p[0]), p[1]) for p in projects],
                on_change=self.update_charts,
                width=300
            )
            
            self.chart_container = ft.Container(
                content=ft.Text("Sélectionnez un projet pour voir les graphiques"),
                padding=20
            )
            
            content = ft.Column([
                ft.Text("Graphiques de Répartition des Coûts", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                project_dropdown,
                ft.Container(height=20),
                self.chart_container
            ])
        
        self.content_area.content = content
        self.page.update()
    
    def update_charts(self, e):
        """Mettre à jour les graphiques selon le projet sélectionné"""
        if not e.control.value:
            return
        
        project_id = int(e.control.value)
        projects = self.db.get_projects()
        project_name = next((p[1] for p in projects if p[0] == project_id), "Projet")
        
        total_cost, category_costs = self.db.get_project_total_cost(project_id)
        
        if total_cost == 0:
            self.chart_container.content = ft.Text("Aucune donnée pour ce projet")
            self.page.update()
            return
        
        # Préparer les données pour le graphique
        chart_data = []
        colors_list = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"
        ]
        
        sorted_categories = sorted(category_costs.items(), key=lambda x: x[1], reverse=True)
        
        for i, (cat_key, cost) in enumerate(sorted_categories):
            if cost > 0:
                percentage = (cost / total_cost) * 100
                cat_name = self.categories.get(cat_key, cat_key)
                chart_data.append({
                    "category": cat_name,
                    "cost": cost,
                    "percentage": percentage,
                    "color": colors_list[i % len(colors_list)]
                })
        
        # Créer le graphique en barres horizontales
        bar_chart_items = []
        max_cost = max(item["cost"] for item in chart_data) if chart_data else 1
        
        for item in chart_data:
            bar_width = (item["cost"] / max_cost) * 400  # largeur maximale de 400px
            
            bar_item = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(
                            item["category"][:20] + "..." if len(item["category"]) > 20 else item["category"],
                            size=12,
                            weight=ft.FontWeight.BOLD
                        ),
                        width=150,
                        padding=5
                    ),
                    ft.Container(
                        bgcolor=item["color"],
                        width=bar_width,
                        height=25,
                        border_radius=5,
                        content=ft.Text(
                            f"{item['cost']}FCFA ({item['percentage']:.1f}%)",
                            size=10,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD
                        ),
                        padding=ft.padding.only(left=10, top=5)
                    )
                ]),
                margin=ft.margin.only(bottom=10)
            )
            bar_chart_items.append(bar_item)
        
        # Créer un graphique en secteurs simplifié
        pie_segments = []
        start_angle = 0
        
        for item in chart_data:
            angle = (item["percentage"] / 100) * 360
            
            pie_segment = ft.Container(
                width=30,
                height=30,
                bgcolor=item["color"],
                border_radius=15,
                content=ft.Text(
                    f"{item['percentage']:.1f}%",
                    size=8,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER
                ),
                padding=5,
                tooltip=f"{item['category']}: {item['cost']}FCFA"
            )
            pie_segments.append(pie_segment)
        
        # Légende
        legend_items = []
        for item in chart_data:
            legend_item = ft.Row([
                ft.Container(
                    width=20,
                    height=20,
                    bgcolor=item["color"],
                    border_radius=5
                ),
                ft.Text(
                    f"{item['category']}: {item['cost']}FCFA ({item['percentage']:.1f}%)",
                    size=12
                )
            ])
            legend_items.append(legend_item)
        
        # Assemblage final
        charts_content = ft.Column([
            ft.Text(f"Répartition des coûts - {project_name}", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(f"Coût total: {total_cost}FCFA", size=14, color=ft.Colors.BLUE),
            ft.Divider(),
            
            ft.Row([
                # Graphique en barres
                ft.Container(
                    content=ft.Column([
                        ft.Text("Graphique en barres", size=16, weight=ft.FontWeight.BOLD),
                        ft.Column(bar_chart_items, scroll=ft.ScrollMode.AUTO)
                    ]),
                    width=600,
                    padding=20
                ),
                
                # Légende
                ft.Container(
                    content=ft.Column([
                        ft.Text("Légende", size=16, weight=ft.FontWeight.BOLD),
                        ft.Column(legend_items, scroll=ft.ScrollMode.AUTO)
                    ]),
                    width=400,
                    padding=20
                )
            ])
        ], scroll=ft.ScrollMode.AUTO)
        
        self.chart_container.content = charts_content
        self.page.update()
    
    def go_to_categories(self, e=None):
        """Retourner aux catégories du projet"""
        self.show_project_categories()
        self.page.update()
    
    def delete_item(self, category_key, item_id):
        try:
            self.db.delete_item(category_key, item_id)
            self.show_snack_bar("Élément supprimé", ft.Colors.GREEN)
            self.manage_category(category_key)  # Refresh
        except Exception as ex:
            self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
    
    def delete_project_confirm(self, project):
        def confirm_delete_handler(e):
            try:
                self.db.delete_project(project[0])
                self.show_snack_bar("Projet supprimé", ft.Colors.GREEN)
                self.show_home_page()
                self.page.update()
                self.page.close(self.confir)
            except Exception as ex:
                self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
        
        def cancel_delete_handler(e):
            self.page.close(self.confir)
        
        self.confir = ft.AlertDialog(
            modal=True,
            visible=True,
            title=ft.Text("Confirmation de suppression"),
            content=ft.Text(f"Êtes-vous sûr de vouloir supprimer le projet '{project[1]}' ?"),
            actions=[
                ft.TextButton("Annuler", on_click=cancel_delete_handler),
                ft.TextButton("Supprimer", on_click=confirm_delete_handler)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: self.page.close(self.confir),
            bgcolor=ft.Colors.WHITE,
        )
        
        self.page.open(self.confir)
        self.page.update()
    
    def show_estimation_page(self):
        """Page de récapitulatif des estimations"""
        projects = self.db.get_projects()
        
        if not projects:
            def create_new_project_handler(e):
                self.nav_rail.selected_index = 1
                self.show_new_project_page()
                self.page.update()
                
            content = ft.Column([
                ft.Text("Aucun projet pour les estimations", size=20),
                ft.ElevatedButton(
                    "Créer un projet",
                    on_click=create_new_project_handler
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            estimation_rows = []
            grand_total = 0
            
            for project in projects:
                total_cost, _ = self.db.get_project_total_cost(project[0])
                grand_total += total_cost
                
                def edit_project_handler(e, p=project):
                    self.edit_project(p)
                
                def export_pdf_handler(e, p=project):
                    self.export_project_pdf(p)
                
                estimation_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(project[1])),
                            ft.DataCell(ft.Text(project[3])),
                            ft.DataCell(ft.Text(f"{total_cost} FCFA")),
                            ft.DataCell(
                                ft.Row([
                                    ft.ElevatedButton(
                                        "Détails",
                                        on_click=edit_project_handler
                                    ),
                                    ft.ElevatedButton(
                                        "PDF",
                                        icon=ft.Icons.PICTURE_AS_PDF,
                                        on_click=export_pdf_handler
                                    ),
                                ])
                            ),
                        ]
                    )
                )
            
            content = ft.Column([
                ft.Text("Récapitulatif des Estimations", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Total général: {grand_total} FCFA", size=18, color=ft.Colors.GREEN),
                ft.Divider(),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Projet")),
                        ft.DataColumn(ft.Text("Date création")),
                        ft.DataColumn(ft.Text("Coût total")),
                        ft.DataColumn(ft.Text("Actions")),
                    ],
                    rows=estimation_rows,
                )
            ])
        
        self.content_area.content = content
        self.page.update()
    
    def show_snack_bar(self, message: str, color: str):
        """Afficher un message de notification"""
        snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color,
        )
        self.page.snack_bar = snack_bar
        snack_bar.open = True
        self.page.update()


    
class BDApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.page = None
        self.category_cards = []
        self.password = "Proseen2025"
        self.is_authenticated = False
    
    def show_password_form(self):
        """Afficher le formulaire de mot de passe"""
        self.password_field = ft.TextField(
            label="Mot de passe",
            password=True,
            hint_text="Entrez le mot de passe",
            width=300,
            on_submit=self.check_password
        )
        
        def check_password_handler(e):
            self.check_password(e)
        
        password_form = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.LOCK, size=80, color=ft.Colors.BLUE_600),
                ft.Text("Accès à la Base de Données", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Accès restreint - Mot de passe requis", size=14, color=ft.Colors.GREY_600),
                ft.Container(height=30),
                self.password_field,
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton(
                        "Accéder",
                        icon=ft.Icons.LOGIN,
                        on_click=check_password_handler,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.BLUE_600,
                            color=ft.Colors.WHITE
                        )
                    ),
                    ft.ElevatedButton(
                        "Retour",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=self.go_to_home
                    )
                ], alignment=ft.MainAxisAlignment.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.WHITE,
            padding=40,
            border_radius=15,
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=10,
                color=ft.Colors.BLACK12,
            )
        )
        
        main_container = ft.Container(
            content=password_form,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_50,
            expand=True
        )
        self.page.controls.clear()
        self.page.add(main_container)
        self.page.update()
    
    def check_password(self, e):
        """Vérifier le mot de passe"""
        if self.password_field.value == self.password:
            self.is_authenticated = True
            self.show_database_interface()
            self.show_snack_bar("Accès autorisé", ft.Colors.GREEN)
        else:
            self.show_snack_bar("Mot de passe incorrect", ft.Colors.RED)
            self.password_field.value = ""
            self.page.update()
    
    def show_database_interface(self):
        """Afficher l'interface de gestion de la base de données"""
        self.page.controls.clear()
        self.page.title = "Gestion de la Base de Données"
        
        # AppBar
        self.page.appbar = ft.AppBar(
            leading_width=50,
            title=ft.Text("Gestion de la base de données", size=30, weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.Colors.BLUE_100,
            actions=[
                ft.IconButton(
                    ft.Icons.INFO,
                    tooltip="À propos",
                    on_click=lambda e: self.show_snack_bar("Application de gestion des coûts de projets", ft.Colors.BLUE_700)
                ),
                ft.IconButton(
                    ft.Icons.HOME,
                    tooltip="Page d'accueil",
                    on_click=self.go_to_home
                ),
            ]
        )
        
        # Créer les cartes des catégories
        self.category_cards = []
        for cat_key, cat_name in self.categories.items():
            def manage_category_handler(e, cat=cat_key):
                self.manage_category(cat)
            
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.CATEGORY),
                            title=ft.Text(cat_name, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Gérer les éléments de la catégorie {cat_name}"),
                        ),
                        ft.ElevatedButton(
                            "Gérer",
                            icon=ft.Icons.SETTINGS,
                            on_click=manage_category_handler
                        )
                    ]),
                    padding=10
                ),
                width=300
            )
            self.category_cards.append(card)
        
        content = ft.Column([
            ft.Text("Catégories de la Base de Données", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.GridView(
                self.category_cards,
                runs_count=3,
                max_extent=300,
                child_aspect_ratio=1.2,
                spacing=10,
                run_spacing=10,
            ),
            ft.Container(height=20)
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.page.add(content)
        self.page.update()
    
    def manage_category(self, category_key):
        """Gérer les éléments d'une catégorie dans la BD"""
        category_name = self.categories[category_key]
        table_name = f"{category_key}_templates"
        
        # Récupérer tous les éléments de cette catégorie (tous projets confondus)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT DISTINCT description, prix_unitaire 
            FROM {table_name} 
            ORDER BY description
        """)
        items = cursor.fetchall()
        conn.close()
        
        # Formulaire d'ajout
        desc_field = ft.TextField(label="Description", width=300)
        price_field = ft.TextField(label="Prix unitaire (FCFA)", width=150)
        
        def add_item_handler(e):
            if not all([desc_field.value, price_field.value]):
                self.show_snack_bar("Tous les champs sont requis", ft.Colors.RED)
                return
            
            try:
                # Ajouter à la BD avec projet_id = 0 (éléments de référence)
                self.db.add_template_item(
                    category_key,
                    desc_field.value,
                    float(price_field.value)
                )
                desc_field.value = ""
                price_field.value = ""
                self.manage_category(category_key)  # Refresh
                self.show_snack_bar("Élément ajouté à la base de données", ft.Colors.GREEN)
            except ValueError:
                self.show_snack_bar("Le prix doit être numérique", ft.Colors.RED)
            except Exception as ex:
                self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
        
        # Liste des éléments
        items_list = []
        for item in items:
            def delete_item_handler(e, desc=item[0]):
                self.delete_reference_item(category_key, desc)
            
            item_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item[0])),  # description
                    ft.DataCell(ft.Text(f"{item[1]}")),  # prix_unitaire
                    ft.DataCell(
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            on_click=delete_item_handler
                        )
                    ),
                ]
            )
            items_list.append(item_row)
        
        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Description")),
                ft.DataColumn(ft.Text("Prix unitaire")),
                ft.DataColumn(ft.Text("Action")),
            ],
            rows=items_list,
        ) if items_list else ft.Text("Aucun élément de référence")
        
        self.page.controls.clear()
        content = ft.Column([
            ft.Text(f"Base de Données - {category_name}", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Formulaire d'ajout
            ft.Text("Ajouter un élément de référence:", weight=ft.FontWeight.BOLD),
            ft.Row([desc_field, price_field]),
            ft.ElevatedButton("Ajouter", icon=ft.Icons.ADD, on_click=add_item_handler),
            
            ft.Container(height=20),
            ft.Text("Éléments de référence:", weight=ft.FontWeight.BOLD),
            data_table,
            
            ft.Container(height=20),
            ft.ElevatedButton(
                "Retour aux catégories",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda e: self.show_database_interface()
            )
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.page.add(content)
        self.page.update()
    
    def delete_reference_item(self, category_key, description):
        """Supprimer un élément de référence"""
        table_name = f"{category_key}_templates"
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE projet_id = 0 AND description = ?", (description,))
            conn.commit()
            conn.close()
            
            self.show_snack_bar("Élément supprimé", ft.Colors.GREEN)
            self.manage_category(category_key)  # Refresh
        except Exception as ex:
            self.show_snack_bar(f"Erreur: {str(ex)}", ft.Colors.RED)
    
    def go_to_home(self, e=None):
        """Retourner à la page d'accueil"""
        self.page.controls.clear()  # Clear existing controls
        self.page.appbar = None     # Remove appbar
        welcome_page = WelcomePage(self.page)
        welcome_content = welcome_page.create_welcome_content()
        self.page.add(welcome_content)
        self.page.update()
    
    def main(self, page: ft.Page):
        """Initialiser la page de la base de données"""
        self.page = page
        page.title = "Base de Données"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1200
        page.window_height = 800
        page.padding = 20
        logo_path = get_asset_path("icon.ico")
        self.page.window_icon = logo_path
        
        self.categories = {
            "logistique_transport": "Logistique & Transport",
            "materiel_electrique": "Matériel Électrique",
            "materiel_genie_civil": "Matériel Génie Civil",
            "materiel_instrumentation": "Matériel Instrumentation",
            "ingenieur_process": "Ingénieur Process",
            "materiel_tuyauterie": "Matériel Tuyauterie",
            "main_oeuvre_electric": "Main d'œuvre Électrique",
            "main_oeuvre_installation": "Main d'œuvre Installation",
            "main_oeuvre_tuyauterie": "Main d'œuvre Tuyauterie"
        }
        
        # Afficher le formulaire de mot de passe
        self.show_password_form()
    
    def show_snack_bar(self, message: str, color: str):
        """Afficher un message de notification"""
        snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color,
        )
        self.page.snack_bar = snack_bar
        snack_bar.open = True
        self.page.update()


class WelcomePage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.logo_path = get_asset_path("icon.ico")
        print("Logo path:", self.logo_path)
        page.window_icon = self.logo_path
        self.app = CostEstimationApp()

    def main(self):
        """Initialiser la page de bienvenue"""
        self.page.title = "Bienvenue dans l'Application d'Estimation des Coûts de Projets"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 1200
        self.page.window_height = 800
        self.page.padding = 0
        self.page.add(self.create_welcome_content())
    
    def create_welcome_content(self):
        """Créer le contenu de la page de bienvenue"""

        def access_projects(e):
            """Accéder à la gestion des projets"""
            self.page.controls.clear()  # Clear existing controls
            main_app = CostEstimationApp()
            main_app.main(self.page)
            self.page.update()
        
        def bd_projects(e):
            """Accéder à la base de données"""
            self.page.controls.clear()  # Clear existing controls
            main_app = BDApp()
            main_app.main(self.page)
            self.page.update()
        
        # Logo ou icône principale
        main_icon = ft.Container(
            content=ft.Icon(
                ft.Icons.CALCULATE,
                size=100,
                color=ft.Colors.BLUE_600
            ),
            alignment=ft.alignment.center,
            padding=20
        )
        
        # Titre principal
        title = ft.Text(
            "Estimation des Coûts de Projets",
            size=36,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_800,
            text_align=ft.TextAlign.CENTER
        )
        
        # Sous-titre
        subtitle = ft.Text(
            "Logiciel professionnel pour l'estimation des coûts",
            size=18,
            color=ft.Colors.GREY_700,
            text_align=ft.TextAlign.CENTER
        )
        
        # Bouton principal d'accès
        access_button = ft.ElevatedButton(
            text="Accéder aux Projets",
            icon=ft.Icons.ARROW_FORWARD,
            on_click=access_projects,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=ft.padding.symmetric(horizontal=30, vertical=15)
            ),
            width=250,
            height=60
        )

        bd_button = ft.ElevatedButton(
            text="Accéder à la Base de Données",
            icon=ft.Icons.ARROW_FORWARD,
            on_click=bd_projects,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=ft.padding.symmetric(horizontal=30, vertical=15)
            ),
            width=250,
            height=60
        )
        
        # Conteneur principal de bienvenue
        welcome_container = ft.Container(
            content=ft.Column([
                main_icon,
                title,
                ft.Container(height=10),
                subtitle,
                ft.Container(height=40),
                access_button,
                ft.Container(height=10),
                bd_button
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.WHITE,
            padding=50,
            border_radius=15,
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=10,
                color=ft.Colors.BLACK12,
            )
        )
        
        # Conteneur avec fond gradient
        main_container = ft.Container(
            content=welcome_container,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_50,
            expand=True,
            padding=40
        )
        
        return main_container
    

def main(page: ft.Page):
    app = WelcomePage(page)
    app.main()
    
    

if __name__ == "__main__":
    ft.app(target=main)