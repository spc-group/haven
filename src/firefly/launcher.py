import argparse
import asyncio
import cProfile
import logging
import pstats
import sys
import time
from pathlib import Path

from pydm import config
from pydm.utilities import setup_renderer
from qasync import QEventLoop
from qtpy import QtCore
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QSplashScreen, QStyleFactory

from firefly.controller import FireflyController


def main(default_fullscreen=False, default_display="status"):
    log = logging.getLogger("")
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)-8s] - %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel("INFO")
    handler.setLevel("INFO")

    try:
        """
        We must import QtWebEngineWidgets before creating a QApplication
        otherwise we get the following error if someone adds a WebView at Designer:
        ImportError: QtWebEngineWidgets must be imported before a QCoreApplication instance is created
        """
    except ImportError:
        log.debug("QtWebEngine is not supported.")

    # Set up splash screen
    app = QApplication(sys.argv)
    im_dir = Path(__file__).parent.resolve()
    im_fp = str(im_dir / "splash.png")
    pixmap = QPixmap(im_fp)
    splash = QSplashScreen(pixmap, QtCore.Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()
    for i in range(10):
        time.sleep(0.01)
    app.processEvents()

    # Set EPICS as the default protocol
    config.DEFAULT_PROTOCOL = "ca"

    ui_folder = Path(__file__).parent.resolve()

    setup_renderer()

    parser = argparse.ArgumentParser(description="Python Display Manager")
    parser.add_argument(
        "display",
        help="The name of a Firefly display to open.",
        nargs="?",
        default=default_display,
    )
    parser.add_argument(
        "--no-instrument",
        action="store_true",
        help=(
            "Do not try to create devices. Useful for development if much beamline"
            " hardware is offline."
        ),
    )
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help=(
            "Do not try to connect to the queueserver. Useful for development if queueserver"
            " hardware is offline."
        ),
    )
    parser.add_argument(
        "--perfmon",
        action="store_true",
        help="Enable performance monitoring," + " and print CPU usage to the terminal.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable cProfile function profiling, printing on exit.",
    )
    parser.add_argument(
        "--hide-menu-bar",
        action="store_true",
        help="Start PyDM with the menu bar hidden.",
    )
    parser.add_argument(
        "--hide-status-bar",
        action="store_true",
        help="Start PyDM with the status bar hidden.",
    )
    if default_fullscreen:
        parser.add_argument(
            "--no-fullscreen",
            dest="fullscreen",
            action="store_false",
            help="Start Firefly in normal (non-fullscreen) mode.",
        )
    else:
        parser.add_argument(
            "--fullscreen",
            action="store_true",
            help="Start Firefly in full screen mode.",
        )
    parser.add_argument(
        "--read-only", action="store_true", help="Start Firefly in a Read-Only mode."
    )
    parser.add_argument(
        "--log_level",
        help="Configure level of log display",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    )
    # parser.add_argument(
    #     "--version",
    #     action="version",
    #     version="Firefly {version}".format(version=haven.__version__),
    #     help="Show Firefly's version number and exit.",
    # )
    parser.add_argument(
        "-m",
        "--macro",
        help="Specify macro replacements to use, in JSON object format."
        + "    Reminder: JSON requires double quotes for strings, "
        + "so you should wrap this whole argument in single quotes."
        + '  Example: -m \'{"sector": "LI25", "facility": "LCLS"}\''
        + "--or-- specify macro replacements as KEY=value pairs "
        + " using a comma as delimiter  If you want to uses spaces "
        + " after the delimiters or around the = signs, "
        + " wrap the entire set with quotes "
        + '  Example: -m "sector = LI25, facility=LCLS"',
    )
    parser.add_argument(
        "--stylesheet",
        help="Specify the full path to a CSS stylesheet file, which"
        + " can be used to customize the appearance of Firefly and"
        + " Qt widgets.",
        default=None,
    )
    parser.add_argument(
        "display_args",
        help="Arguments to be passed to the PyDM client application"
        + " (which is a QApplication subclass).",
        nargs=argparse.REMAINDER,
        default=None,
    )

    pydm_args = parser.parse_args()
    if pydm_args.profile:
        profile = cProfile.Profile()
        profile.enable()

    if pydm_args.log_level:
        log.setLevel(pydm_args.log_level)
        handler.setLevel(pydm_args.log_level)

    controller = FireflyController(
        display=pydm_args.display,
    )
    qss_file = Path(__file__).parent / "firefly.qss"
    app.setStyleSheet(qss_file.read_text())
    # apply_stylesheet(app.stylesheet_path, widget=main_window)
    log.info(f"Available styles: {QStyleFactory.keys()}")

    # Make it asynchronous
    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    async def run_app():
        # Keep an event to know when the app has closed
        app_close_event = asyncio.Event()
        app.aboutToQuit.connect(app_close_event.set)
        # Define devices on the beamline (slow!)
        await controller.setup_instrument(load_instrument=not pydm_args.no_instrument)
        # Start any async clients that the controller needs
        if not pydm_args.no_queue:
            controller.start()
        # Get rid of the splash screen and show the first window
        splash.close()
        controller.show_default_window()
        # Wait on the application to finish
        await app_close_event.wait()

    # Start the actual asyncio event loop
    event_loop.run_until_complete(run_app())
    event_loop.close()

    if pydm_args.profile:
        profile.disable()
        stats = pstats.Stats(
            profile,
            stream=sys.stdout,
        ).sort_stats(pstats.SortKey.CUMULATIVE)
        stats.print_stats()


def cameras():
    main(default_fullscreen=True, default_display="cameras")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
