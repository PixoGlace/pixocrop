# Detection et impression PDF

Ce document decrit le chemin suivi entre une page PDF source et le travail transmis au pilote d'impression.

## Detection locale

La detection reste entierement locale et n'utilise ni OCR, ni IA, ni modele d'apprentissage.

1. Les regles de transporteurs existantes sont evaluees en premier.
2. Des candidats geometriques sont construits a partir des cadres vectoriels, blocs d'images, ancres de type code-barres ou QR code, zones denses et regroupements de contenu.
3. Chaque candidat recoit un score explicable selon sa densite, ses marges, son rapport largeur/hauteur, sa couverture de page et ses ancres.
4. Les candidats presque identiques sont fusionnes par intersection sur union.
5. Les zones proches d'une page A4 complete et les zones ressemblant a une notice sont penalisees.
6. La zone de contenu generique n'est retenue que si aucun candidat n'atteint le seuil de confiance.

`DetectionResult` expose la zone retenue, les candidats classes et l'utilisation eventuelle du repli. L'interface continue de stocker un `PdfRect` par page afin que la selection puisse etre dessinee, deplacee et redimensionnee manuellement.

## Papier et orientation

`PaperSpec` conserve les dimensions physiques independamment de `PageOrientation`. Les dimensions sont normalisees en portrait pour construire le `QPageSize`, puis l'orientation est appliquee exactement une fois par `QPageLayout`.

Les tailles annoncees par le pilote sont recherchees avec une tolerance de 1 mm. Un format personnalise n'est construit que si aucune taille compatible n'est disponible. Une taille pilote declaree directement en paysage est normalisee avant de passer a Qt, ce qui evite une seconde inversion.

Exemples garantis :

- papier 70 x 50 mm avec orientation paysage : sortie 70 x 50 mm ;
- papier 50 x 70 mm avec orientation portrait : sortie 50 x 70 mm.

### Note de migration

Avant cette correction, certains formats personnalises etaient enregistres avec leurs dimensions deja inversees, puis inverses une seconde fois par l'orientation Qt. Les choix ne sont pas persistes dans la version actuelle de pixoCrop. Lors d'une future persistance, il faudra stocker la cle `PaperSpec` et l'orientation separement, jamais une paire de dimensions deja orientee.

## Apercu et rendu

`compute_target_rect()` est la source unique pour le placement et la mise a l'echelle. L'aperçu et l'impression lui transmettent les memes dimensions physiques, marges, option d'adaptation et zoom.

`plan_render()` calcule :

- le rectangle final dans les pixels du peripherique ;
- la resolution de rasterisation utile ;
- l'echelle physique ;
- la memoire estimee ;
- les avertissements de forte reduction, haute resolution et limite de pixels.

Le rendu PyMuPDF est dimensionne pour le rectangle final. Les echantillons RGB du pixmap sont copies directement vers `QImage`, sans encodage PNG intermediaire. Une page est rendue et peinte a la fois.

La limite par defaut est `12_000_000` pixels. Elle est configuree par `PIXO_MAX_RENDER_PIXELS` et chargee dans `src/pixocrop/config.py`.

## Validation du pilote

`apply_printer_settings()` journalise et compare :

- taille demandee et taille acceptee ;
- orientation demandee et orientation acceptee ;
- resolution demandee et resolution acceptee ;
- utilisation du format par defaut comme solution de repli.

Le flux verifie egalement `QPainter.begin()`, `QPrinter.newPage()`, `QPainter.end()` et l'etat final de l'imprimante. Un refus de format propose explicitement de continuer avec le format par defaut du pilote.

Les diagnostics sont conserves dans `pixocrop.log`, sous le repertoire de donnees local de l'application retourne par `QStandardPaths.AppLocalDataLocation`. Le fichier est limite a 1 Mo avec deux sauvegardes tournantes.

## Strategie de test

Les tests geometriques generent des PDF minimaux en memoire. Les refus de pilote sont reproduits avec un faux pilote deterministe. Les tests d'integration utilisent le moteur PDF de `QPrinter`, puis rouvrent le resultat avec PyMuPDF pour verifier les dimensions physiques et la presence de l'image.

Le fichier externe `TikTokSeller.pdf` est utilise en lecture seule lorsqu'il est present dans l'environnement local. Le test verifie sa zone geometrique et une impression virtuelle a 300 dpi sur 70 x 50 mm. Il est ignore proprement dans les environnements CI qui ne possedent pas ce fixture prive.
