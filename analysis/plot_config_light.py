import seaborn as sns
from cycler import cycler


def in2pt(inches):
    return inches * 72.27


def pt2in(pt):
    return pt/72.27


# Constants (two column publication format)
LATEX_TEXT_WIDTH_PT = 505.89
LATEX_TEXT_WIDTH_IN = pt2in(LATEX_TEXT_WIDTH_PT)
LATEX_LINE_WIDTH_PT = 241.02039
LATEX_LINE_WIDTH_IN = pt2in(LATEX_LINE_WIDTH_PT)
GOLDEN_RATIO = (5**.5 - 1) / 2


def get_fig_size_paper(xscale=1.0, yscale=1.0, full=False):
    # https://jwalton.info/Embed-Publication-Matplotlib-Latex/
    width = LATEX_LINE_WIDTH_IN
    if full:
        width = LATEX_TEXT_WIDTH_IN
    height = (width * GOLDEN_RATIO)
    return (width * xscale, height * yscale)


# Default microsoft power point text box sizes
PPT_LINE_HEIGHT_IN = 4.76
PPT_LINE_WIDTH_IN = 5.67
PPT_TEXT_WIDTH_IN = 11.5


def get_fig_size_ppt(xscale=1.0, yscale=1.0, full=False):
    # https://jwalton.info/Embed-Publication-Matplotlib-Latex/
    width = PPT_LINE_WIDTH_IN
    height = width * GOLDEN_RATIO
    if full:
        height = PPT_LINE_HEIGHT_IN
        width = height / GOLDEN_RATIO
    return (width * xscale, height * yscale)


def get_entries(cycle_list, num_entries):
    n = len(cycle_list)
    m = int(num_entries / n) + 1
    return (cycle_list * m)[:num_entries]


colors = sns.color_palette('tab10')
n_colors = len(colors)
available_linestyles = ['solid', 'dashdot', 'dashed']
linestyles = get_entries(available_linestyles, n_colors)

# https://matplotlib.org/stable/api/markers_api.html
available_markers = ['o', '^', 's', '*', 'X', 'd']
markers = get_entries(available_markers, n_colors)

# https://matplotlib.org/stable/gallery/shapes_and_collections/hatch_style_reference.html
available_hatches = ['', '//', '\\\\', '||', '--', '++', 'xx']
hatches = get_entries(available_hatches, n_colors)

# Map from colors to hatches, markers and line styles
# Useful when using manual colors for lines/objects
hatch_map = {colors[i]: hatch for i,
                    hatch in enumerate(hatches)}
marker_map = {colors[i]: marker for i,
                    marker in enumerate(markers)}
ls_map = {colors[i]: ls for i, ls in enumerate(linestyles)}


BIG_SIZE=7.0  # 8.0
SMALL_SIZE=6.0  # 7.0
PAPER_STYLE = {
    "figure.dpi": 600,
    "font.family": "sans-serif",
    # "font.sans-serif": [
    #     "Arial",
    #     "Source Sans 3",
    #     "Aptos",
    #     "Tahoma",
    #     "Computer Modern",
    #     "DejaVu Sans",
    #     "Helvetica",
    #     "Lucida Grande",
    #     "Verdana",
    # ],
    "font.size": BIG_SIZE,
    "axes.labelsize": BIG_SIZE,
    "legend.fontsize": SMALL_SIZE,
    "xtick.labelsize": SMALL_SIZE,
    "ytick.labelsize": SMALL_SIZE,
    "pdf.fonttype": 42,
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "axes.grid": True,
    "grid.linestyle": "--",
    "axes.linewidth": 0.5,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.minor.width": 0.4,
    "ytick.minor.width": 0.4,
    "lines.linewidth": 1,
    "lines.markersize": 3,
    "lines.markeredgewidth": 0.5,
    "legend.handlelength": 2.5,
    "hatch.linewidth": 0.5,
    "grid.linewidth": 0.25,
    "axes.titlesize": BIG_SIZE,
    "legend.title_fontsize": BIG_SIZE,
}

PPT_STYLE = {
    "figure.dpi": 600,
    "font.family": "sans-serif",
    "font.sans-serif": ["Source Sans 3"],
    "font.size": 24,
    "axes.labelsize": 24,
    "legend.fontsize": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    # "pgf.texsystem": "pdflatex",
    # "text.usetex": True,
    # "pgf.preamble": "\\usepackage[utf8]{inputenc}\n\\usepackage[T1]{fontenc}\n\\usepackage{usenix}",
    # "text.latex.preamble": "\\usepackage[cm]{sfmath}\n\\usepackage{amsmath}",
    "pdf.fonttype": 42,
    "axes.grid": True,
    "grid.linestyle": "--",
    "axes.linewidth": 1.5,
    "xtick.major.width": 1.5,
    "ytick.major.width": 1.5,
    "xtick.minor.width": 1,
    "ytick.minor.width": 1,
    "lines.linewidth": 2.5,
    "grid.linewidth": 1,
    "xtick.major.size": 8,
    "xtick.minor.size": 4,
    "ytick.major.size": 8,
    "ytick.minor.size": 4,
    "axes.titlesize": 24,
    "legend.title_fontsize": 24,
}

USE_TEX = {
    "pgf.texsystem": "pdflatex",
    "text.usetex": True,
    "pgf.preamble": "\\usepackage[utf8]{inputenc}\n\\usepackage[T1]{fontenc}\n\\usepackage{usenix}",
    "text.latex.preamble": "\\usepackage[cm]{sfmath}\n\\usepackage{amsmath}",
}


def get_style(use_markers=False, paper=True, use_tex=False):
    cycling = (cycler('color', colors)
                + cycler('ls', linestyles))
    if use_markers:
        cycling += cycler('marker', markers)

    ret = PPT_STYLE.copy()
    if paper:
        ret = PAPER_STYLE.copy()
    if use_tex:
        ret.update(USE_TEX)
    ret['axes.prop_cycle'] = cycling
    return ret