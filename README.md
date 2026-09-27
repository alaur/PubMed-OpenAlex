Voici une documentation complète et claire du projet, prête à être conservée ou partagée sous forme de fichier README.md.

Système de Veille Bibliographique Médicale Automatisée

Carcinome Hépatocellulaire (CHC) & Cholangiocarcinome (CCA)

Ce projet met en place un pipeline de veille scientifique automatisé et souverain sur macOS (optimisé pour Apple Silicon). Il interroge chaque semaine la base de données internationale OpenAlex, extrait les publications parues sur les 14 derniers jours, filtre strictement les revues à très haut facteur d’impact (> 9,0), fait traduire et synthétiser les résumés par un grand modèle de langage exécuté localement, génère un rapport PDF et prépare l'envoi du message dans l'application native Mail de macOS.

1. Architecture et fonctionnement

Pour chaque pathologie ciblée, le pipeline exécute les étapes suivantes :

OpenAlex API (Requête Polite Pool)
       │
       ▼
Filtrage qualité (Score d'impact 2yr > 9,0)
       │
       ▼
Traduction & Synthèse médicale (LLM local : Gemma 4 12B MLX)
       │
       ▼
Mise en page PDF (ReportLab) -> ~/.hermes/skills/[veille]_watch/
       │
       ▼
Génération et envoi de l'e-mail (AppleScript / Mail.app)


Arborescence des fichiers

⚬ ~/.hermes/skills/hcc_watch/hcc_weekly.py : Veille sur le carcinome hépatocellulaire.
⚬ ~/.hermes/skills/hcc_watch/HCC-news-J8.pdf : Rapport PDF généré pour le CHC.
⚬ ~/.hermes/skills/cca_watch/cca_weekly.py : Veille sur le cholangiocarcinome et les voies biliaires.
⚬ ~/.hermes/skills/cca_watch/CCA-news-J8.pdf : Rapport PDF généré pour le CCA.

2. Prérequis matériels et logiciels

1. Mac avec puce Apple Silicon (M1/M2/M3/M4) avec au minimum 16 Go de mémoire unifiée.
2. Ollama ou MLX installé et actif en local avec le modèle chargé :
   ollama pull gemma4:12b-mlx
   
3. Bibliothèques Python requises :
   pip3 install requests reportlab urllib3
   
4. Droits d'automatisation macOS : l'accès de contrôle entre le Terminal et l'application Mail doit être autorisé dans Réglages Système > Confidentialité et sécurité > Automatisation.

3. Configuration et Installation

A. Récupération des scripts

Les scripts sont stockés dans le répertoire des compétences de l'agent :

mkdir -p ~/.hermes/skills/hcc_watch
mkdir -p ~/.hermes/skills/cca_watch


B. Paramètres clés configurés dans les scripts

⚬ API OpenAlex : mettre ses codes persos
⚬ Seuil d'impact : score_float > 9.0 (moyenne de citations sur deux ans de la revue source).
⚬ Modèle d'inférence : gemma4:12b-mlx.
⚬ Destinataire du rapport : alexis.laurent@aphp.fr.

4. Utilisation

Exécution manuelle à la demande

Pour lancer immédiatement une veille et tester la chaîne de traitement complète :

⚬ Pour le carcinome hépatocellulaire (CHC) :
  /Library/Developer/CommandLineTools/usr/bin/python3 ~/.hermes/skills/hcc_watch/hcc_weekly.py
  
⚬ Pour le cholangiocarcinome (CCA) :
  /Library/Developer/CommandLineTools/usr/bin/python3 ~/.hermes/skills/cca_watch/cca_weekly.py
  

Le script affiche en direct le nombre d'articles extraits, les revues retenues, le statut de traduction de chaque résumé par le modèle local, puis génère le PDF et ouvre le message correspondant dans Mail.app.

5. Automatisation hebdomadaire (Crontab)

Pour que la veille s'exécute de façon totalement autonome en arrière-plan sans intervention humaine, deux tâches planifiées cron sont enregistrées (espacées pour éviter une surcharge simultanée de la mémoire unifiée) :

1. Ouvrir la table d'automatisation :
   crontab -e
   
2. Ajouter la planification (exemple : CHC le samedi matin et CCA le dimanche matin) :
   # Veille CHC : tous les samedis à 06 h 00
   0 6 * * 6 /Library/Developer/CommandLineTools/usr/bin/python3 /Users/al-macmini-m4/.hermes/skills/hcc_watch/hcc_weekly.py >> /Users/al-macmini-m4/scripts/hcc_cron.log 2>&1
   
   # Veille Cholangiocarcinome : tous les dimanches à 06 h 00
   0 6 * * 0 /Library/Developer/CommandLineTools/usr/bin/python3 /Users/al-macmini-m4/.hermes/skills/cca_watch/cca_weekly.py >> /Users/al-macmini-m4/scripts/cca_cron.log 2>&1
   
3. Suivre les journaux d'exécution en cas de besoin :
   tail -f ~/scripts/cca_cron.log
