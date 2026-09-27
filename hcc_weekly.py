#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime, timedelta
import requests
import ollama
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

EMAIL_OPENALEX = "alexis.laurent@mac.com"
EMAIL_DEST = "alexis.laurent@aphp.fr"
PDF_PATH = os.path.expanduser("~/scripts/hcc_watch/HCC-news-J8.pdf")
HEADERS = {"User-Agent": "HCCWatch/1.0 (mailto:alexis.laurent@mac.com)"}

JOURNAL_CACHE = {}

def get_journal_citedness(source_id):
    if not source_id:
        return 0.0
    sid = source_id.split("/")[-1]
    if sid in JOURNAL_CACHE:
        return JOURNAL_CACHE[sid]
    
    try:
        url = f"https://api.openalex.org/sources/{sid}?mailto=alexis.laurent@mac.com"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            score = r.json().get("summary_stats", {}).get("2yr_mean_citedness", 0.0)
            score_float = float(score) if score else 0.0
            JOURNAL_CACHE[sid] = score_float
            return score_float
    except Exception:
        pass
    
    JOURNAL_CACHE[sid] = 0.0
    return 0.0

def reconstruct_abstract(inverted_index):
    if not inverted_index:
        return "Aucun abstract disponible."
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)

def fetch_openalex_articles(days_back=14):
    print(f"-> Recherche d'articles HCC parus les {days_back} derniers jours...")
    from_date = (datetime.today() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    to_date = datetime.today().strftime('%Y-%m-%d')
    
    # Filtres stricts : vrais articles de revues, période valide, langue anglaise
    filters = (
        f"from_publication_date:{from_date},"
        f"to_publication_date:{to_date},"
        f"title.search:hepatocellular carcinoma,"
        f"type:article,"
        f"primary_location.source.type:journal,"
        f"language:en"
    )
    
    url = "https://api.openalex.org/works"
    params = {
        "filter": filters,
        "per-page": 100,
        "api_key": "oDEq2IikFeLYwixifll3iF",
        "mailto": "alexis.laurent@mac.com"
    }
    
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"Erreur API OpenAlex ({r.status_code}) : {r.text}")
        return []
    
    raw_results = r.json().get("results", [])
    print(f"   {len(raw_results)} articles de revues trouvés. Filtrage sur score revue > 9.0...")
    
    selected_articles = []
    for work in raw_results:
        source = (work.get("primary_location") or {}).get("source") or {}
        source_id = source.get("id")
        journal_name = source.get("display_name", "Revue non spécifiée")
        
        citedness = get_journal_citedness(source_id)
        
        if citedness > 9.0:
            title = work.get("title") or "Sans titre"
            ids = work.get("ids", {})
            pubmed_url = ids.get("pmid")
            pmid = pubmed_url.split("/")[-1] if pubmed_url else None
            abstract_raw = reconstruct_abstract(work.get("abstract_inverted_index"))
            
            print(f"   [RETENU] {journal_name} (Score: {citedness:.2f}) -> {title[:60]}...")
            
            selected_articles.append({
                "title": title,
                "pmid": pmid,
                "pubmed_url": pubmed_url or f"https://doi.org/{work.get('doi', '')}",
                "journal": journal_name,
                "citedness": citedness,
                "abstract_raw": abstract_raw,
                "pub_date": work.get("publication_date", "Date inconnue")
            })
            
    print(f"-> {len(selected_articles)} article(s) retenu(s).")
    return selected_articles

def translate(text):
    if text == "Aucun abstract disponible." or not text.strip():
        return text
    prompt = (
        "Tu es un traducteur médical spécialisé en oncologie hépatique. "
        "Traduis ce résumé d'article de l'anglais vers le français de manière rigoureuse. "
        "Ne génère aucun commentaire, préambule ou formule de politesse :\n\n"
        f"{text}"
    )
    res = ollama.chat(model="gemma4:12b-mlx", messages=[{"role": "user", "content": prompt}])
    return res["message"]["content"].strip()

def build_pdf(articles, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=colors.HexColor('#0f2b48'), spaceAfter=8)
    art_title = ParagraphStyle('AT', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#003366'), spaceAfter=4)
    meta_style = ParagraphStyle('M', fontName='Helvetica-Oblique', fontSize=8.5, leading=11, textColor=colors.HexColor('#555555'), spaceAfter=6)
    body_style = ParagraphStyle('B', fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)

    today_str = datetime.today().strftime('%d/%m/%Y')
    story = [
        Paragraph("Veille Hebdomadaire — Carcinome Hépatocellulaire (HCC)", title_style),
        Paragraph(f"Date du rapport : {today_str} | Filtre : Revues médicales avec 2yr_mean_citedness > 9", meta_style),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366'), spaceAfter=12)
    ]

    if not articles:
        story.append(Paragraph("<b>Aucun article avec 2yr_mean_citedness > 9 identifié sur la période.</b>", body_style))
    else:
        for art in articles:
            link = art['pubmed_url']
            story.append(Paragraph(f"<a href='{link}'><u>{art['title']}</u></a>", art_title))
            
            ref_id = f"PMID : <a href='{link}'><u>{art['pmid']}</u></a>" if art['pmid'] else f"<a href='{link}'><u>Lien Article / DOI</u></a>"
            meta_info = f"Revue : <b>{art['journal']}</b> | Score 2yr_citedness : <b>{art['citedness']:.2f}</b> | Date : {art['pub_date']} | {ref_id}"
            story.append(Paragraph(meta_info, meta_style))
            
            abstract_html = art['abstract_fr'].replace('\n', '<br/>')
            story.append(Paragraph(abstract_html, body_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=10))

    doc.build(story)

def send_apple_mail(dest, subject, body_text, attachment):
    safe_body = body_text.replace('"', '\\"')
    applescript = f'''
    tell application "Mail"
        set msg to make new outgoing message with properties {{subject:"{subject}", content:"{safe_body}" & return & return, visible:false}}
        tell msg
            make new to recipient at end of to recipients with properties {{address:"{dest}"}}
            make new attachment with properties {{file name:"{attachment}" as POSIX file}} at after the last paragraph
            send
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript], check=True)

def main():
    articles = fetch_openalex_articles(days_back=14)
    
    if articles:
        for idx, art in enumerate(articles, 1):
            print(f"[{idx}/{len(articles)}] Traduction abstract Gemma 4 12B MLX : {art['journal']} (Score {art['citedness']:.1f})")
            art['abstract_fr'] = translate(art['abstract_raw'])
    
    print("-> Génération du document PDF...")
    import os
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
    build_pdf(articles, PDF_PATH)
    
    if articles:
        body = f"Veuillez trouver ci-joint la veille bibliographique HCC (14 derniers jours).\nNombre d'articles retenus (revues score > 9.0) : {len(articles)}."
    else:
        body = "Aucun article avec 2yr_mean_citedness > 9 cette semaine.\nVeuillez trouver le rapport PDF récapitulatif en pièce jointe."

    print(f"-> Envoi du mail à {EMAIL_DEST}...")
    send_apple_mail(EMAIL_DEST, "HCC-news-J8", body, PDF_PATH)
    print("Succès ! Pipeline exécuté et message envoyé.")

if __name__ == "__main__":
    main()
