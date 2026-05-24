"""
create_pdf_sample.py
Génération d'un PDF de test pour le Module 1
Simule un document réglementaire public (guide pratique employeur)
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

os.makedirs("data/public", exist_ok=True)

filepath = "data/public/guide_embauche_employeur.pdf"
doc = SimpleDocTemplate(filepath, pagesize=A4)
styles = getSampleStyleSheet()
content = []

content.append(Paragraph("Guide pratique — Embauche d'un salarié", styles["Title"]))
content.append(Spacer(1, 20))

content.append(Paragraph("1. Déclaration préalable à l'embauche (DPAE)", styles["Heading1"]))
content.append(Paragraph(
    "Tout employeur doit effectuer une Déclaration Préalable à l'Embauche (DPAE) "
    "auprès de l'URSSAF avant toute embauche. Cette déclaration doit être effectuée "
    "au plus tôt 8 jours avant l'embauche et au plus tard au moment de l'embauche. "
    "La DPAE permet l'immatriculation du salarié à la Sécurité sociale, "
    "l'affiliation à l'assurance chômage et la déclaration aux caisses de retraite.",
    styles["Normal"]
))
content.append(Spacer(1, 12))

content.append(Paragraph("2. Contrat de travail", styles["Heading1"]))
content.append(Paragraph(
    "Le contrat de travail doit être établi par écrit pour les CDD et les contrats "
    "à temps partiel. Pour les CDI à temps plein, un écrit n'est pas obligatoire "
    "mais fortement recommandé. Le contrat doit préciser la nature du poste, "
    "la rémunération, la durée du travail et la convention collective applicable.",
    styles["Normal"]
))
content.append(Spacer(1, 12))

content.append(Paragraph("3. Visite médicale d'embauche", styles["Heading1"]))
content.append(Paragraph(
    "Le salarié doit bénéficier d'une visite d'information et de prévention (VIP) "
    "dans les 3 mois suivant la prise de poste. Pour les postes à risques, "
    "un examen médical d'aptitude est requis avant la prise de poste. "
    "L'employeur prend en charge les frais de la visite médicale.",
    styles["Normal"]
))
content.append(Spacer(1, 12))

content.append(Paragraph("4. Période d'essai", styles["Heading1"]))
content.append(Paragraph(
    "La durée maximale de la période d'essai est de 2 mois pour les ouvriers "
    "et employés, 3 mois pour les agents de maîtrise et techniciens, "
    "et 4 mois pour les cadres. La période d'essai peut être renouvelée "
    "une fois si un accord de branche le prévoit.",
    styles["Normal"]
))
content.append(Spacer(1, 12))

content.append(Paragraph("5. Registre du personnel", styles["Heading1"]))
content.append(Paragraph(
    "Tout employeur doit tenir un registre unique du personnel. "
    "Ce registre doit mentionner pour chaque salarié : nom, prénom, "
    "nationalité, date de naissance, sexe, emploi, qualification, "
    "date d'entrée et de sortie. Il doit être conservé pendant 5 ans "
    "après le départ du salarié.",
    styles["Normal"]
))

doc.build(content)
print(f"PDF créé : {filepath}")