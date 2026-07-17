# pixoCrop

Application Python avec interface graphique pour detecter un bordereau d'expedition dans un PDF, recadrer uniquement cette region, puis lancer l'impression via le lecteur PDF/systeme.

Projet maintenu par PixoGlace.

## Installation developpement

```bash
make dev
make run
```

Si `make run` ne montre pas les dernieres modifications, verifiez le fichier Python
reellement lance avec :

```bash
make run-info
```

La commande doit afficher `src/pixocrop/app.py`.

## Configuration principale

Les informations principales du projet sont centralisees dans
`src/pixocrop/config.py` :

- nom de l'application ;
- version ;
- licence ;
- lien du projet ;
- lien et texte de donation.

Les langues de l'interface sont configurees dans
`src/pixocrop/language_config.py`. Les langues disponibles sont :

- francais ;
- anglais ;
- arabe ;
- chinois.

L'utilisateur peut changer la langue depuis `Outils > Parametres`.

## Mises a jour

Au lancement, pixoCrop verifie silencieusement la derniere release GitHub via
`UPDATE_CHECK_URL` dans `src/pixocrop/config.py`. Si une version plus recente
que `VERSION` est disponible, l'application propose d'ouvrir la page de
telechargement.

## Utilisation

1. Ouvrir un PDF avec le bouton `Ouvrir PDF`, ou deposer directement un fichier PDF dans l'aperçu.
2. Cliquer sur `Auto detecter`.
3. Verifier la zone bleue dans l'aperçu et ajuster la marge si besoin.
4. Si la zone n'est pas correcte, dessiner directement un nouveau rectangle sur la partie a imprimer.
5. Pour deplacer la zone, cliquer dans le rectangle bleu puis glisser.
6. Utiliser `Appliquer a toutes` si la meme zone doit etre imprimee sur toutes les pages.
7. Exporter le PDF recadre ou cliquer sur `Imprimer`.

Dans l'aperçu, le rectangle bleu transparent represente la zone qui sera imprimee. `Ctrl + molette` permet de zoomer.

Le bouton `Imprimer` ouvre une fenetre interne avec l'aperçu de la zone selectionnee, le choix de l'imprimante, les copies, l'orientation, le format papier, la qualite, le mode couleur, le recto-verso et l'adaptation a la page.

## Build executable

```bash
make release-linux
```

Sur Linux, la release genere un executable autonome avec PyInstaller en mode `--onefile`.
La release genere aussi un paquet Debian `.deb`. L'archive finale est placee
dans `release/` et contient :

- `pixoCrop`, l'executable complet a double-cliquer apres extraction ;
- `bin/pixoCrop`, un lien vers l'executable pour l'installation locale ;
- un fichier `.desktop` ;
- l'icone de l'application ;
- `README-linux.txt` avec les commandes d'installation locale optionnelle.

Sur macOS, la release produit aussi un `.dmg` avec l'application et un lien
vers `/Applications`. Sur Windows, la CI produit un installateur `.exe` avec
Inno Setup.

Le design des paquets est genere au moment du packaging par
`packaging/create_packaging_art.py` :

- fond du DMG macOS ;
- images de l'assistant d'installation Windows ;
- banniere/metadonnees visuelles Linux.

La creation du DMG utilise `create-dmg` si l'outil est disponible, puis revient
sur `hdiutil` en secours. L'installateur Windows utilise Inno Setup.

## CI/CD et releases GitHub

Le workflow GitHub Actions construit les binaires Linux, Windows et macOS.

- Sur `push` et `pull_request`, les binaires sont construits et disponibles comme artefacts de workflow.
- Sur un tag `v*`, une Release GitHub est creee automatiquement avec les archives telechargeables par la vitrine.

Le workflow de developpement `.github/workflows/dev-build.yml` est separe :

- il se lance uniquement lors d'un push vers une branche commencant par `dev`, par exemple `dev-med` ou `dev/impression` ;
- il construit Linux, Windows, macOS Intel et macOS Apple Silicon sans publier de GitHub Release ;
- ses artefacts portent le nom du compte ayant lance le push et sont supprimes apres 7 jours ;
- chaque binaire portable et chaque installateur sont exposes comme des artefacts distincts ;
- leur acces suit les droits de lecture du depot. Un depot prive les reserve donc aux collaborateurs autorises. GitHub ne propose pas de restriction par artefact pour un depot public.

Les artefacts de l'onglet Actions sont toujours telecharges dans une enveloppe ZIP geree par GitHub.
Les boutons de la vitrine utilisent les assets de la GitHub Release : chaque fichier y est
telechargeable directement et independamment.

Exemple :

```bash
git tag v0.1.0
git push origin v0.1.0
```

Archives publiees :

- `pixoCrop-linux-x86_64.tar.gz`
- `pixocrop_<version>_amd64.deb`
- `pixoCrop-windows-x64.zip`
- `pixoCrop-windows-x64-setup.exe`
- `pixoCrop-macos-arm64.zip`
- `pixoCrop-macos-arm64.dmg`
- `pixoCrop-macos-x86_64.zip`
- `pixoCrop-macos-x86_64.dmg`

## Site vitrine

La documentation vitrine est dans `docs/`.

Pour la publier avec GitHub Pages :

1. Ouvrir les parametres du depot GitHub.
2. Aller dans `Pages`.
3. Choisir la branche principale et le dossier `/docs`.
4. Enregistrer.

## Donation

Si pixoCrop vous aide, vous pouvez soutenir le projet :

[Buy Me a Coffee](https://www.buymeacoffee.com/pixoglace)

Ces informations sont aussi accessibles dans l'application via `Aide > A propos de pixoCrop`.

## Licence

pixoCrop est distribue sous licence GNU General Public License v3.0 (GPL-3.0).
Voir [LICENSE](LICENSE).

## Copyright et marques

Copyright (C) 2026 PixoGlace. Voir [COPYRIGHT](COPYRIGHT).

Les noms PixoGlace et PixoCrop, le logo, les icones et l'identite visuelle du
projet restent reserves a PixoGlace. Voir [TRADEMARKS.md](TRADEMARKS.md).
