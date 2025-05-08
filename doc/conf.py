"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# Authors: The MNE-Python contributors.
# License: BSD-3-Clause
# Copyright the MNE-Python contributors.

import faulthandler
import os
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import metadata
from pathlib import Path

import matplotlib
import sphinx
#from intersphinx_registry import get_intersphinx_mapping
from numpydoc import docscrape
from sphinx.config import is_serializable
from sphinx.domains.changeset import versionlabels
from sphinx_gallery.sorting import ExplicitOrder

#import whobpyt

import mne
import mne.html_templates._templates

linkcode_resolve = None

# assert linkcode_resolve is not None  # avoid flake warnings, used by numpydoc
matplotlib.use("agg")
faulthandler.enable()
# https://numba.readthedocs.io/en/latest/reference/deprecation.html#deprecation-of-old-style-numba-captured-errors  # noqa: E501
mne.html_templates._templates._COLLAPSED = False #  True  # collapse info _repr_html_


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
curpath = Path(__file__).parent.resolve(strict=True)
sys.path.append(str(curpath / "sphinxext"))



# -- Project information -----------------------------------------------------

project = "WhoBPyT"
td = datetime.now(tz=timezone.utc)

# We need to triage which date type we use so that incremental builds work
# (Sphinx looks at variable changes and rewrites all files if some change)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = "6.0"
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # builtin
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.graphviz",
    # "sphinx.ext.intersphinx",
    #"sphinx.ext.linkcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.todo",
    # contrib
    "matplotlib.sphinxext.plot_directive",
    "numpydoc",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.youtube",
    "sphinxcontrib.towncrier.ext",
    # homegrown
#    "contrib_avatars",
#    "gen_commands",
#    "gen_names",
#    "gh_substitutions",
#    "mne_substitutions",
#    "newcontrib_substitutions",
#   "unit_role",
#    "related_software",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.

# NB: changes here should also be made to the linkcheck target in the Makefile
exclude_patterns = ["_includes", "changes/devel"]

# The suffix of source filenames.
source_suffix = [".rst", ".md"]

# The main toctree document.
master_doc = "index"

# List of documents that shouldn't be included in the build.
unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched for source files.
exclude_trees = ["_build"]

# The reST default role (used for this markup: `text`) to use for all documents.
defaut_role = "py:obj"

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = [] # ["mne."]

# -- Sphinx-Copybutton configuration -----------------------------------------
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# -- sphinxcontrib-towncrier configuration -----------------------------------
towncrier_draft_working_directory = str(curpath.parent)

# NumPyDoc configuration -----------------------------------------------------

numpydoc_attributes_as_param_list = True
numpydoc_xref_param_type = True


# -- Sphinx-gallery configuration --------------------------------------------

examples_dirs = ["../examples"] # ["../tutorials", "../examples"]
gallery_dirs = ["auto_examples"] # ["auto_tutorials", "auto_examples"]

compress_images = ("images", "thumbnails")
# let's make things easier on Windows users
# (on Linux and macOS it's easy enough to require this)
if sys.platform.startswith("win"):
    try:
        subprocess.check_call(["optipng", "--version"])
    except Exception:
        compress_images = ()

sphinx_gallery_conf = {
    "doc_module": ("whobpyt",),
    "reference_url": dict(whobpyt=None),
    "examples_dirs": examples_dirs,
    "subsection_order": ExplicitOrder(
        [
            "../examples/eg__tmseeg",
            "../examples/eg__ismail2025",
            "../examples/eg__momi2023",
            "../examples/eg__momi2025",
        ]
    ),
    "gallery_dirs": gallery_dirs,
    "default_thumb_file": os.path.join("_static", "whobpyt_logo_feet.png"),
    "backreferences_dir": "generated",
    "plot_gallery": "True",  # Avoid annoying Unicode/bool default warning
    "thumbnail_size": (160, 112),
    "remove_config_comments": True,
    "min_reported_time": 1.0,
    "abort_on_example_error": False,
    "reset_modules_order": "both",
    "show_memory": sys.platform == "linux" , #and sphinx_gallery_parallel == 1,
    "line_numbers": False,  # messes with style
    "within_subsection_order": "FileNameSortKey",
    "capture_repr": ("_repr_html_",),
    "junit": os.path.join("..", "test-results", "sphinx-gallery", "junit.xml"),
    "matplotlib_animations": True,
    "compress_images": compress_images,
    "filename_pattern": "^((?!sgskip).)*$",
    "exclude_implicit_doc": {},
    "show_api_usage": "unused",
    "copyfile_regex": r".*index\.rst" #,  # allow custom index.rst files
    }
 
assert is_serializable(sphinx_gallery_conf)
# Files were renamed from plot_* with:
# find . -type f -name 'plot_*.py' -exec sh -c 'x="{}"; xn=`basename "${x}"`; git mv "$x" `dirname "${x}"`/${xn:5}' \;  # noqa


def append_attr_meth_examples(app, what, name, obj, options, lines):
    """Append SG examples backreferences to method and attr docstrings."""
    # NumpyDoc nicely embeds method and attribute docstrings for us, but it
    # does not respect the autodoc templates that would otherwise insert
    # the .. include:: lines, so we need to do it.
    # Eventually this could perhaps live in SG.
    if what in ("attribute", "method"):
        size = os.path.getsize(
            os.path.join(
                os.path.dirname(__file__),
                "generated",
                f"{name}.examples",
            )
        )
        if size > 0:
            lines += """
.. _sphx_glr_backreferences_{1}:

.. rubric:: Examples using ``{0}``:

.. minigallery:: {1}

""".format(name.split(".")[-1], name).split("\n")



# -- Other extension configuration -------------------------------------------

# Consider using http://magjac.com/graphviz-visual-editor for this
graphviz_dot_args = [
    "-Gsep=-0.5",
    "-Gpad=0.5",
    "-Nshape=box",
    "-Nfontsize=20",
    "-Nfontname=Open Sans,Arial",
]
graphviz_output_format = "svg"  # for API usage diagrams
user_agent = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Mobile Safari/537.36"  # noqa: E501
# Can eventually add linkcheck_request_headers if needed
linkcheck_ignore = [  # will be compiled to regex
    # 403 Client Error: Forbidden
    "https://doi.org/10.1002/",  # onlinelibrary.wiley.com/doi/10.1002/hbm
    "https://doi.org/10.1016/",  # neuroimage
    "https://doi.org/10.1021/",  # pubss.org/doi/abs
    "https://doi.org/10.1063/",  # pubs.aip.org/aip/jap
    "https://doi.org/10.1073/",  # pnas.org
    "https://doi.org/10.1080/",  # www.tandfonline.com
    "https://doi.org/10.1088/",  # www.tandfonline.com
    "https://doi.org/10.1093/",  # academic.oup.com/sleep/
    "https://doi.org/10.1098/",  # royalsocietypublishing.org
    "https://doi.org/10.1101/",  # www.biorxiv.org
    "https://doi.org/10.1103",  # journals.aps.org/rmp
    "https://doi.org/10.1111/",  # onlinelibrary.wiley.com/doi/10.1111/psyp
    "https://doi.org/10.1126/",  # www.science.org
    "https://doi.org/10.1137/",  # epubs.siam.org
    "https://doi.org/10.1145/",  # dl.acm.org
    "https://doi.org/10.1155/",  # www.hindawi.com/journals/cin
    "https://doi.org/10.1161/",  # www.ahajournals.org
    "https://doi.org/10.1162/",  # direct.mit.edu/neco/article/
    "https://doi.org/10.1167/",  # jov.arvojournals.org
    "https://doi.org/10.1177/",  # journals.sagepub.com
    "https://doi.org/10.3109/",  # www.tandfonline.com
    "https://www.biorxiv.org/content/10.1101/",  # biorxiv.org
    "https://www.researchgate.net/profile/",
    "https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html",
    r"https://scholar.google.com/scholar\?cites=12188330066413208874&as_ylo=2014",
    r"https://scholar.google.com/scholar\?cites=1521584321377182930&as_ylo=2013",
    "https://www.research.chop.edu/imaging",
    "http://prdownloads.sourceforge.net/optipng",
    "https://sourceforge.net/projects/aespa/files/",
    "https://sourceforge.net/projects/ezwinports/files/",
    "https://www.mathworks.com/products/compiler/matlab-runtime.html",
    "https://medicine.umich.edu/dept/khri/ross-maddox-phd",
    # 500 server error
    "https://openwetware.org/wiki/Beauchamp:FreeSurfer",
    # 503 Server error
    "https://hal.archives-ouvertes.fr/hal-01848442",
    # Read timed out
    "http://www.cs.ucl.ac.uk/staff/d.barber/brml",
    "https://www.cea.fr",
    "http://www.humanconnectome.org/data",
    "https://www.mail-archive.com/freesurfer@nmr.mgh.harvard.edu",
    "https://launchpad.net",
    # Max retries exceeded
    "https://doi.org/10.7488/ds/1556",
    "https://datashare.is.ed.ac.uk/handle/10283",
    "https://imaging.mrc-cbu.cam.ac.uk/imaging/MniTalairach",
    "https://www.nyu.edu/",
    # Too slow
    "https://speakerdeck.com/dengemann/",
    "https://www.dtu.dk/english/service/phonebook/person",
    "https://www.gnu.org/software/make/",
    "https://www.macports.org/",
    "https://hastie.su.domains/CASI",
    # SSL problems sometimes
    "http://ilabs.washington.edu",
    "https://psychophysiology.cpmc.columbia.edu",
    "https://erc.easme-web.eu",
    # Not rendered by linkcheck builder
    r"ides\.html",
]
linkcheck_anchors = False  # saves a bit of time
linkcheck_timeout = 15  # some can be quite slow
linkcheck_retries = 3
linkcheck_report_timeouts_as_broken = False

# autodoc / autosummary
autosummary_generate = True
autodoc_default_options = {"inherited-members": None}

# sphinxcontrib-bibtex
bibtex_bibfiles = ["./references.bib"]
bibtex_style = "unsrt"
bibtex_footbibliography_header = ""


# -- Nitpicky ----------------------------------------------------------------

nitpicky = True
show_warning_types = True
nitpick_ignore = [
    ("py:class", "None.  Remove all items from D."),
    ("py:class", "a set-like object providing a view on D's items"),
    ("py:class", "a set-like object providing a view on D's keys"),
    (
        "py:class",
        "v, remove specified key and return the corresponding value.",
    ),  # noqa: E501
    ("py:class", "None.  Update D from dict/iterable E and F."),
    ("py:class", "an object providing a view on D's values"),
    ("py:class", "a shallow copy of D"),
    ("py:class", "(k, v), remove and return some (key, value) pair as a"),
    ("py:class", "_FuncT"),  # type hint used in @verbose decorator
#    ("py:class", "mne.utils._logging._FuncT"),
    ("py:class", "None.  Remove all items from od."),
]
nitpick_ignore_regex = [
    # Classes whose methods we purposefully do not document
#    ("py:.*", r"mne\.io\.BaseRaw.*"),  # use mne.io.Raw
#    ("py:.*", r"mne\.BaseEpochs.*"),  # use mne.Epochs
    # Type hints for undocumented types
#    ("py:.*", r"mne\.io\..*\.Raw.*"),  # RawEDF etc.
#    ("py:.*", r"mne\.epochs\.EpochsFIF.*"),
#    ("py:.*", r"mne\.io\..*\.Epochs.*"),  # EpochsKIT etc.
    (  # BaseRaw attributes are documented in Raw
        "py:obj",
        "(filename|metadata|proj|times|tmax|tmin|annotations|ch_names"
        "|compensation_grade|duration|filenames|first_samp|first_time"
        "|last_samp|n_times|proj|times|tmax|tmin)",
    ),
]
suppress_warnings = [
    "image.nonlocal_uri",  # we intentionally link outside
]


# -- Sphinx hacks / overrides ------------------------------------------------

versionlabels["versionadded"] = sphinx.locale._("New in v%s")

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# switcher_version_match = "dev" if ".dev" in version else version
html_theme_options = {
    "icon_links": [
        dict(
            name="GitHub",
            url="https://github.com/griffithslab/whobpyt",
            icon="fa-brands fa-square-github fa-fw",
        ),
    ],
    "icon_links_label": "External Links",  # for screen reader
    "use_edit_page_button": False,
    "navigation_with_keys": False,
    "show_toc_level": 1,
    "show_nav_level": 0,
    "navigation_depth": 4,
    "article_header_start": [],  # disable breadcrumbs
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],   # ← lives in the middle
    "navbar_end": [
        "theme-switcher", #"version-switcher",
        "navbar-icon-links"],#, "toggle-sidebar.html"],
    "navbar_align": "left", # left
    "navbar_persistent": ["search-button"],
    "collapse_navigation": False, #True, # False, # True,
    "footer_start": ["copyright"],
    "secondary_sidebar_items": ["page-toc", "edit-this-page"],
    "analytics": dict(google_analytics_id="G-5TBCPCRB6X"),
    #"switcher": { "json_url": "https://mne.tools/dev/_static/versions.json", "version_match": switcher_version_match,
    "back_to_top_button": False,
    "logo": {
        "image_light": "_static/whobpyt_logo_feet.png",
        "image_dark": "_static/whobpyt_logo_feet_dark.png",
    }
}


# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "_static/favicon.ico"


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = ['style.css', 'css/fix-sidebar.css']

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    "auto_examples/**": [],          # ← hide left sidebar on every example page
    '**': ["sidebar-nav-bs.html"]}

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False
html_copy_source = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# accommodate different logo shapes (width values in rem)
xs = "2"
sm = "2.5"
md = "3"
lg = "4.5"
xl = "5"
xxl = "6"
# variables to pass to HTML templating engine
html_context = {
    "default_mode": "auto",
    # next 3 are for the "edit this page" button
    "github_user": "griffithslab",
    "github_repo": "whobpyt",
    "github_version": "main",
    "doc_path": "doc",
    #"funders": [ dict(img="nih.svg", size="3", title="CAMH"), dict(img="nsf.png", size="3.5", title="CIHR"),dict( img="erc.svg", size="3.5", title="UofT", klass="only-light"),],
    "institutions": [
        dict(
            name="University of Toronto",
            img="UofT_logo.jpg",
            url="https://www.utoronto.ca/",
            size=xl,
        ),
        dict(
            name="Krembil Centre for Neuroinformatics",
            img="KCNI_logo.png",
            url="https://www.krembilneuroinformatics.ca/",
            size=xl,
        ),
        dict(
            name="Center for Addiction and Mental Health",
            img="CAMH_logo_purple.png",
            url="https://www.camh.ca/",
            size=xl,
        ),
        dict(
            name="Hospital for Sick Children",
            img="sick_kids_logo.png",
            url="https://www.sickkids.ca/",
            size=xl,
        )
    ],
    # \u00AD is an optional hyphen (not rendered unless needed)
    # If these are changed, the Makefile should be updated, too
    "carousel": [
        dict(
            title="Brain Dynamics",
            text="oscillations, functional connectivity, brain network organization", 
            url="documentation/science/brain_dynamics/index.html",
            img="../_static/Ismail2025_SummaryFigure.png",
            alt="dSPM",
        ),
        dict(
            title="Brain Stimulation",
            text="electrical/magnetic/acoustic, invasive/noninvasive brain stimulation",
            url="documentation/science/brain_stimulation/index.html",
            img="../_static/momi2025__SummaryFigure.png",
            alt="Stimulation",
        ),
        dict(
            title="Brain & Cognition",
            text="evoked/induced activity during cognitive tasks",
            url="documentation/science/brain_cognition/index.html",
            img="../_static/Ismail2025_SummaryFigure.png",
            alt="Cognition",
        ),
    ],
}

html_theme = "pydata_sphinx_theme"

# Output file base name for HTML help builder.
htmlhelp_basename = "whobpyt-doc"


# -- Options for plot_directive ----------------------------------------------

# Adapted from SciPy
plot_include_source = True
plot_formats = [("png", 96)]
plot_html_show_formats = False
plot_html_show_source_link = False
font_size = 13 * 72 / 96.0  # 13 px
plot_rcparams = {
    "font.size": font_size,
    "axes.titlesize": font_size,
    "axes.labelsize": font_size,
    "xtick.labelsize": font_size,
    "ytick.labelsize": font_size,
    "legend.fontsize": font_size,
    "figure.figsize": (6, 5),
    "figure.subplot.bottom": 0.2,
    "figure.subplot.left": 0.2,
    "figure.subplot.right": 0.9,
    "figure.subplot.top": 0.85,
    "figure.subplot.wspace": 0.4,
    "text.usetex": False,
}


# -- Options for LaTeX output ------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = []

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = "_static/logo.png"

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
latex_toplevel_sectioning = "part"

# -- Warnings management -----------------------------------------------------
#reset_warnings(None, None)

# -- Fontawesome support -----------------------------------------------------
brand_icons = ("apple", "linux", "windows", "discourse", "python")
fixed_width_icons = (
    # homepage:
    "book",
    #"code-branch",
    "newspaper",
    "circle-question",
    "quote-left",
    # contrib guide:
    "bug-slash",
    "comment",
    "computer-mouse",
    "hand-sparkles",
    "pencil",
    "text-slash",
    "universal-access",
    "wand-magic-sparkles",
    "discourse",
    "python",
)
other_icons = (
    "hand-paper",
    "question",
    "rocket",
    "server",
    "code",
    "desktop",
    "terminal",
    "cloud-arrow-down",
    "wrench",
    "hourglass-half",
)
icon_class = dict()
for icon in brand_icons + fixed_width_icons + other_icons:
    icon_class[icon] = ("fa-brands",) if icon in brand_icons else ("fa-solid",)
    icon_class[icon] += ("fa-fw",) if icon in fixed_width_icons else ()

rst_prolog = ""
for icon, classes in icon_class.items():
    rst_prolog += f"""
.. |{icon}| raw:: html

    <i class="{" ".join(classes + (f"fa-{icon}",))}"></i>
"""

#rst_prolog += """
#.. |ensp| unicode:: U+2002 .. EN SPACE
#
#.. include:: /links.inc
#.. include:: /changes/names.inc
#
#.. currentmodule:: mne
#"""

# -- Dependency info ----------------------------------------------------------

min_py = metadata("whobpyt")["Requires-Python"].lstrip(" =<>")
rst_prolog += f"\n.. |min_python_version| replace:: {min_py}\n"

# -- website redirects --------------------------------------------------------

# Static list created 2021/04/13 based on what we needed to redirect,
# since we don't need to add redirects for examples added after this date.
needed_plot_redirects = { }
api_redirects = { }
ex = "auto_examples"
co = "connectivity"
mne_conn = "https://mne.tools/mne-connectivity/stable"
tu = "auto_tutorials"
pr = "preprocessing"
di = "discussions"
sm = "source-modeling"
fw = "forward"
nv = "inverse"
sn = "stats-sensor-space"
sr = "stats-source-space"
sd = "sample-datasets"
ml = "machine-learning"
tf = "time-freq"
si = "simulation"
vi = "visualization"
custom_redirects = {}
    # Custom redirects (one HTML path to another, relative to outdir)
    # can be added here as fr->to key->value mappings

# Adapted from sphinxcontrib/redirects (BSD-2-Clause)
REDIRECT_TEMPLATE = """\
<!DOCTYPE HTML>
<html lang="en-US">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="1; url={to}">
        <script type="text/javascript">
            window.location.href = "{to}"
        </script>
        <title>Page Redirection</title>
    </head>
    <body>
        If you are not redirected automatically, follow this <a href='{to}'>link</a>.
    </body>
</html>"""


def check_existing_redirect(path):
    """Make sure existing HTML files are redirects, before overwriting."""
    if path.is_file():
        with open(path) as fid:
            for _ in range(8):
                next(fid)
            line = fid.readline()
            if "Page Redirection" not in line:
                raise RuntimeError(
                    "Attempted overwrite of HTML file with a redirect, where the "
                    "original file was not already a redirect."
                )

def _check_valid_builder(app, exception):
    valid_builder = isinstance(app.builder, sphinx.builders.html.StandaloneHTMLBuilder)
    return valid_builder and exception is None

def make_gallery_redirects(app, exception):
    """Make HTML redirects for our sphinx gallery pages."""
    if not _check_valid_builder(app, exception):
        return
    sg_conf = app.config["sphinx_gallery_conf"]
    for src_dir, out_dir in zip(sg_conf["examples_dirs"], sg_conf["gallery_dirs"]):
        root = (Path(app.srcdir) / src_dir).resolve()
        fnames = [
            pyfile.relative_to(root)
            for pyfile in root.rglob(r"**/*.py")
            if pyfile.name in needed_plot_redirects
        ]
        # plot_ redirects
        for fname in fnames:
            dirname = Path(app.outdir) / out_dir / fname.parent
            to_fname = fname.with_suffix(".html").name
            fr_fname = f"plot_{to_fname}"
            to_path = dirname / to_fname
            fr_path = dirname / fr_fname
            assert to_path.is_file(), (fname, to_path)
            with open(fr_path, "w") as fid:
                fid.write(REDIRECT_TEMPLATE.format(to=to_fname))
        
def make_api_redirects(app, exception):
    """Make HTML redirects for our API pages."""
    if not _check_valid_builder(app, exception):
        return

    for page in api_redirects:
        fname = f"{page}.html"
        fr_path = Path(app.outdir) / fname
        to_path = Path(app.outdir) / "api" / fname
        # allow overwrite if existing file is just a redirect
        check_existing_redirect(fr_path)
        with open(fr_path, "w") as fid:
            fid.write(REDIRECT_TEMPLATE.format(to=to_path))
    #sphinx_logger.info(f"Added {len(api_redirects):3d} HTML API redirects")



# -- Connect our handlers to the main Sphinx app ---------------------------

def setup(app):
    app.add_css_file("css/fix-sidebar.css")
