# pixoCrop

Application Python avec interface graphique pour detecter un bordereau d'expedition dans un PDF, recadrer uniquement cette region, puis lancer l'impression via le lecteur PDF/systeme.

Projet maintenu par PixoGlace.

## Installation developpement

```bash
make dev
make run
```

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
L'archive finale est placee dans `release/` et contient :

- `pixoCrop`, l'executable complet a double-cliquer apres extraction ;
- `bin/pixoCrop`, un lien vers l'executable pour l'installation locale ;
- un fichier `.desktop` ;
- l'icone de l'application ;
- `README-linux.txt` avec les commandes d'installation locale optionnelle.


## CI/CD et releases GitHub

Le workflow GitHub Actions construit les binaires Linux, Windows et macOS.

- Sur `push` et `pull_request`, les binaires sont construits et disponibles comme artefacts de workflow.
- Sur un tag `v*`, une Release GitHub est creee automatiquement avec les archives telechargeables par la vitrine.

Exemple :

```bash
git tag v0.1.0
git push origin v0.1.0
```

Archives publiees :

- `pixoCrop-linux-x86_64.tar.gz`
- `pixoCrop-windows-x64.zip`
- `pixoCrop-macos-arm64.zip`
- `pixoCrop-macos-x86_64.zip`

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

## Licence

pixoCrop est distribue sous licence GNU General Public License v3.0 (GPL-3.0).
Voir [LICENSE](LICENSE).

## Copyright et marques

Copyright (C) 2026 PixoGlace. Voir [COPYRIGHT](COPYRIGHT).

Les noms PixoGlace et PixoCrop, le logo, les icones et l'identite visuelle du
projet restent reserves a PixoGlace. Voir [TRADEMARKS.md](TRADEMARKS.md).
