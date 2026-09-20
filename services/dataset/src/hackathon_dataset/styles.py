from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True, slots=True)
class DocumentStyle:
    style_id: str
    header_layout: str
    background_pattern: str
    title_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    panel_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    page_color: tuple[int, int, int]
    muted_color: tuple[int, int, int]
    badge_text: str
    pdf_title_font: str
    pdf_body_font: str
    image_fonts: tuple[str, ...]
    footer_text: str


STYLES: tuple[DocumentStyle, ...] = (
    DocumentStyle(
        style_id="corporate_blue",
        header_layout="band",
        background_pattern="grid",
        title_color=(19, 83, 138),
        accent_color=(45, 125, 210),
        panel_color=(235, 243, 252),
        border_color=(165, 196, 228),
        page_color=(251, 253, 255),
        muted_color=(95, 115, 140),
        badge_text="Original",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Helvetica",
        image_fonts=("arialbd.ttf", "arial.ttf", "calibri.ttf"),
        footer_text="Service comptabilite fournisseur",
    ),
    DocumentStyle(
        style_id="compliance_green",
        header_layout="boxed",
        background_pattern="dots",
        title_color=(26, 102, 73),
        accent_color=(53, 143, 96),
        panel_color=(235, 248, 240),
        border_color=(168, 210, 186),
        page_color=(251, 255, 252),
        muted_color=(94, 123, 110),
        badge_text="Conforme",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Helvetica",
        image_fonts=("calibrib.ttf", "calibri.ttf", "arial.ttf"),
        footer_text="Document de conformite interne",
    ),
    DocumentStyle(
        style_id="industrial_orange",
        header_layout="ribbon",
        background_pattern="diagonal",
        title_color=(154, 77, 18),
        accent_color=(225, 130, 42),
        panel_color=(255, 244, 233),
        border_color=(236, 196, 157),
        page_color=(255, 252, 249),
        muted_color=(132, 103, 82),
        badge_text="Dossier",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Courier",
        image_fonts=("verdanab.ttf", "verdana.ttf", "arial.ttf"),
        footer_text="Pole achats et approvisionnement",
    ),
    DocumentStyle(
        style_id="heritage_burgundy",
        header_layout="sidebar",
        background_pattern="none",
        title_color=(111, 35, 51),
        accent_color=(165, 62, 90),
        panel_color=(251, 238, 243),
        border_color=(224, 180, 193),
        page_color=(255, 252, 253),
        muted_color=(118, 93, 104),
        badge_text="Archive",
        pdf_title_font="Times-Bold",
        pdf_body_font="Times-Roman",
        image_fonts=("timesbd.ttf", "times.ttf", "georgia.ttf", "arial.ttf"),
        footer_text="Service administratif central",
    ),
    DocumentStyle(
        style_id="tech_slate",
        header_layout="split",
        background_pattern="thin_lines",
        title_color=(40, 56, 72),
        accent_color=(75, 131, 180),
        panel_color=(238, 244, 248),
        border_color=(183, 197, 208),
        page_color=(249, 251, 252),
        muted_color=(92, 107, 118),
        badge_text="Numerise",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Helvetica",
        image_fonts=("segoeuib.ttf", "segoeui.ttf", "arial.ttf"),
        footer_text="Portail fournisseurs numerique",
    ),
    DocumentStyle(
        style_id="civic_red",
        header_layout="band",
        background_pattern="thin_lines",
        title_color=(145, 43, 43),
        accent_color=(205, 79, 79),
        panel_color=(252, 239, 239),
        border_color=(229, 185, 185),
        page_color=(255, 252, 252),
        muted_color=(130, 88, 88),
        badge_text="Prioritaire",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Helvetica",
        image_fonts=("arialbd.ttf", "arial.ttf", "calibri.ttf"),
        footer_text="Service administratif et finance",
    ),
    DocumentStyle(
        style_id="minimal_gray",
        header_layout="boxed",
        background_pattern="none",
        title_color=(70, 76, 82),
        accent_color=(122, 132, 144),
        panel_color=(243, 245, 247),
        border_color=(210, 216, 222),
        page_color=(253, 253, 253),
        muted_color=(120, 126, 133),
        badge_text="Classe",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Courier",
        image_fonts=("segoeuib.ttf", "segoeui.ttf", "arial.ttf"),
        footer_text="Archives et gestion documentaire",
    ),
    DocumentStyle(
        style_id="ocean_teal",
        header_layout="split",
        background_pattern="grid",
        title_color=(24, 95, 107),
        accent_color=(32, 156, 173),
        panel_color=(232, 247, 248),
        border_color=(172, 213, 218),
        page_color=(249, 254, 255),
        muted_color=(82, 123, 128),
        badge_text="Synchronise",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Helvetica",
        image_fonts=("calibrib.ttf", "calibri.ttf", "arial.ttf"),
        footer_text="Backoffice achats et contrats",
    ),
    DocumentStyle(
        style_id="sand_gold",
        header_layout="ribbon",
        background_pattern="dots",
        title_color=(138, 102, 42),
        accent_color=(196, 156, 74),
        panel_color=(251, 246, 233),
        border_color=(227, 209, 164),
        page_color=(255, 254, 249),
        muted_color=(134, 116, 84),
        badge_text="Valide",
        pdf_title_font="Times-Bold",
        pdf_body_font="Times-Roman",
        image_fonts=("timesbd.ttf", "times.ttf", "georgia.ttf", "arial.ttf"),
        footer_text="Direction achats et services",
    ),
    DocumentStyle(
        style_id="midnight_navy",
        header_layout="sidebar",
        background_pattern="diagonal",
        title_color=(27, 49, 87),
        accent_color=(57, 93, 161),
        panel_color=(235, 241, 251),
        border_color=(177, 192, 223),
        page_color=(248, 250, 255),
        muted_color=(87, 104, 133),
        badge_text="Controle",
        pdf_title_font="Helvetica-Bold",
        pdf_body_font="Helvetica",
        image_fonts=("verdanab.ttf", "verdana.ttf", "arial.ttf"),
        footer_text="Cellule audit et verification",
    ),
)


def pick_style(rng: Random) -> DocumentStyle:
    return rng.choice(STYLES)
