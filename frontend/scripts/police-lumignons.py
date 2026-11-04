"""Lumignons : Le Murmure (Jérémy Landes, OFL) avec un C et un c plus calmes.

Usage : uv run --with fonttools --with brotli python -I scripts/police-lumignons.py le-murmure.ttf public/fonts/Lumignons-Regular.woff2

Le terminal du haut de C et c plonge vers l'intérieur et forme une fausse barre de « e »
(« Croix-Rousse » se lisait « Eroix-Rousse »). Les nouvelles lettres gardent le terminal fin
du bas d'origine et lui donnent un miroir en haut, avec une vraie ouverture au milieu.
La licence réserve les noms « Murmure » et « Le Murmure » : la version modifiée s'appelle
« Lumignons ».
"""
import sys
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphComponent, Glyph
from fontTools.ttLib.tables import ttProgram

SOURCE, SORTIE = sys.argv[1], sys.argv[2]
f = TTFont(SOURCE)
glyf = f["glyf"]


def lettre(gauche: int, haut: int, bas_terminal: int, haut_terminal: int):
    """Contour d'un c (x-height `haut`) ou d'un C (capitale `haut`), dans le sens de la police."""
    h = haut  # axe de symétrie : y' = h - y
    def m(y):  # miroir vertical
        return h - y
    pen = TTGlyphPen(None)
    # Terminal du haut, coin extérieur, puis montée du côté droit et arc du haut (vers la gauche).
    pen.moveTo((203, m(bas_terminal)))
    pen.lineTo((204, m(157)))
    pen.qCurveTo((206, m(83)), (161, m(-10)), (117, m(-10)))
    pen.qCurveTo((73 if gauche == 30 else 75, m(-10)), (gauche, m(44)), (gauche, m(107)))
    # Côté gauche, arc du bas, terminal du bas (d'origine, raccourci).
    pen.lineTo((gauche, 107))
    pen.qCurveTo((gauche, 44), (73 if gauche == 30 else 75, -10), (117, -10))
    pen.qCurveTo((161, -10), (206, 83), (204, 157))
    pen.lineTo((203, bas_terminal))
    pen.lineTo((185, bas_terminal))
    pen.lineTo((184, 160))
    # Contre-forme : arc intérieur du bas, côté gauche intérieur, arc intérieur du haut.
    pen.qCurveTo((182, 110), (165, 58), (146, 58))
    pen.qCurveTo((128, 58), (105, 92), (105, 141))
    pen.lineTo((105, m(141)))
    pen.qCurveTo((105, m(92)), (128, m(58)), (146, m(58)))
    pen.qCurveTo((165, m(58)), (182, m(110)), (184, m(160)))
    pen.lineTo((185, m(haut_terminal)))
    pen.closePath()
    g = pen.glyph()
    g.program = ttProgram.Program()
    g.program.fromBytecode(b"")
    return g


# c : x-height 600 (dépassements -10 et 610), ouverture de 190 à 410.
glyf["c"] = lettre(35, 600, 190, 190)
# C : capitale 730 (dépassements -10 et 740), ouverture de 210 à 520.
glyf["C"] = lettre(30, 730, 210, 210)
for nom in ("c", "C"):
    glyf[nom].recalcBounds(glyf)
    largeur, _ = f["hmtx"][nom]
    f["hmtx"][nom] = (largeur, glyf[nom].xMin)


def compose(nom: str, base: str, dx: int) -> None:
    g = Glyph()
    g.numberOfContours = -1
    g.components = []
    for composant, x in ((base, 0), ("cedilla", dx)):
        c = GlyphComponent()
        c.glyphName, c.x, c.y, c.flags = composant, x, 0, 0
        g.components.append(c)
    g.components[0].flags = 0x0200  # USE_MY_METRICS : la chasse du c
    glyf[nom] = g
    g.recalcBounds(glyf)
    f["hmtx"][nom] = (f["hmtx"][base][0], g.xMin)


compose("ccedilla", "c", 0)
compose("Ccedilla", "C", -7)

# Nom : « Murmure » et « Le Murmure » sont réservés par la licence.
nom = f["name"]
for rec in list(nom.names):
    if rec.nameID in (1, 16):
        rec.string = "Lumignons"
    elif rec.nameID == 4:
        rec.string = "Lumignons Regular"
    elif rec.nameID == 6:
        rec.string = "Lumignons-Regular"
    elif rec.nameID == 3:
        rec.string = "1.002;Lumignons-Regular"
    elif rec.nameID == 5:
        rec.string = "Version 1.002 ; Lumignons : C et c redessinés (2026)"
nom.setName("Lumignons est une version modifiée de Le Murmure (Jérémy Landes, Velvetyne), "
            "sous licence SIL OFL 1.1 : C, c, Ç et ç redessinés.", 10, 3, 1, 0x409)
if "DSIG" in f:
    del f["DSIG"]
f["maxp"].recalc(f)
f.flavor = "woff2"
f.save(SORTIE)
print("écrit", SORTIE)
