"""Module for the CSS Status tab."""

import time
from typing import Any

# from trame.widgets.vuetify3 import VIframe
import requests
from nova.trame.view.components import InputField
from nova.trame.view.layouts import VBoxLayout
from selenium.webdriver import Firefox, FirefoxOptions
from trame.widgets import html
from trame.widgets import vuetify3 as vuetify

from ..view_models.main import MainViewModel


class CSSStatusView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()
        self.view_model.update_cssstatus_figure()

    def create_ui(self) -> None:
        with VBoxLayout(columns=1):
            InputField(v_model="model_cssstatus.plot_type", items="model_cssstatus.plot_type_options", type="select")
        # with GridLayout(columns=4):
        # InputField(v_model="model_cssstatus.plot_type", items="model_cssstatus.plot_type_options", type="select")
        # InputField(v_model="model_cssstatus.x_axis", items="model_cssstatus.axis_options", type="select")
        # InputField(v_model="model_cssstatus.y_axis", items="model_cssstatus.axis_options", type="select")
        # InputField(
        #    v_model="model_cssstatus.z_axis",
        #    disabled=("model_cssstatus.is_not_heatmap",),
        #    items="model_cssstatus.axis_options",
        #    type="select",
        # )

        # with HBoxLayout(stretch=True):
        #     # Load the image from the file
        #     # image_path = "/home/zx5/1-todo/6-hardware/code/expgui/ExpHub/webpage.png"
        #     # image = Image.open(image_path)
        #     initial_screenshot = save_webpage_as_image(bl12cssstatus_urlsrc)
        #     image = Image.open(io.BytesIO(initial_screenshot))
        #     width, height = image.size
        #     cropscreen = image.crop((0, int(height * 0), int(width * 0.65), int(height * 1.000)))
        #     screenshot = io.BytesIO()
        #     cropscreen.save(screenshot, format="PNG")
        #     screenshot_bytes = screenshot.getvalue()
        #     image = Image.open(io.BytesIO(screenshot_bytes))

        #     vuetify.VImg(classes="h-100 w-100", src=("model_cssstatus.screenshot",))

        # with VBoxLayout(gap="0.5em", halign="center"):
        #     vuetify.VBtn("Auto Update", click=self.view_model.create_auto_update_cssstatus_figure)
        #     with vuetify.VTab(
        #         href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
        #         raw_attrs=['''target="_blank"'''],
        #     ):
        #         html.Span("Instrument Status", classes="mr-1")
        #         vuetify.VIcon("mdi-open-in-new")


#       # print("obj fig md5sum:" ,dict(self.figure))
##print("obj fig md5sum:" ,self.figure.data["chart_data"])
# print("update_figure")
# while True:
#  self.figure.update(figure)
#  self.figure.state.flush()  #
#  time.sleep(1)
#  #timestamp=time.time()


# TODO: modulize
bl12cssstatus_urlsrc = "https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D"


def save_webpage_as_image_0(url: str, output_file: str = "webpage.png") -> bytes:
    # Configure headless Firefox browser
    options = FirefoxOptions()
    options.add_argument("-headless")
    options.add_argument("--height=10000")

    # Start browser and load page
    browser = Firefox(options=options)
    browser.get(url)

    # Take screenshot and save it
    # time.sleep(5)
    screenshot = browser.get_screenshot_as_png()
    return screenshot


bl12cssstatus_urlsrc = "https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D"


def save_webpage_as_image(url: str, output_file: str = "webpage.png") -> bytes:
    # Configure headless Firefox browser
    options = FirefoxOptions()
    options.add_argument("-headless")
    options.add_argument("--height=10000")

    # Start browser and load page
    browser = Firefox(options=options)
    browser.get(url)

    # Take screenshot and save it
    time.sleep(0.4)
    screenshot = browser.get_screenshot_as_png()
    # with open(output_file, "wb") as file:
    #    file.write(screenshot)
    # print(f"Screenshot saved to {output_file}")

    # Close browser

    return screenshot


# save_webpage_as_image("https://example.com")
# save_webpage_as_image(bl12cssstatus_urlsrc)


class CSSStatusView0:
    """View class for the CSS status."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()

    def create_ui(self) -> None:
        # Create a route that serves the file
        image_path = "webpage.png"  # Absolute path to your image
        import trame

        trame_server = trame.app.get_server()

        @trame_server.controller.add("serve_image")
        def serve_image() -> bytes:
            with open(image_path, "rb") as f:
                image_data = f.read()
            return image_data

        html.Img(src="/api/serve_image", style="width: 100%; height: 100%;")

        html.Div("This is the CSS Status page.")
        htmlt1 = "<html><body><h1>Test Content</h1><p>This is a test.</p></body></html>"
        html.Iframe(
            srcdoc=htmlt1,
        )
        response = requests.get("https://sns.gov/about")
        response = requests.get("https://www.sciencegateway.org/gr/morse.htm")
        print(response.text)
        f = open("temp2.html", "r")
        htmlt2 = f.read()
        html.Iframe(
            srcdoc=htmlt2,
        )
        # html.Iframe( srcdoc=response.text,)
        html.Iframe(src="https://www.sciencegateway.org/gr/morse.htm")
        html.Iframe(
            src="http://0.0.0.0:8000/?url=https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
            classes="fill-height",
        )
        html.Iframe(
            src="http://0.0.0.0:8000/?url=https://google.com",
            classes="fill-height",
            #    style="width: 100%; height: 600px; border: none;"
        )
        html.Iframe(
            src="http://0.0.0.0:8000/?url=https://example.com",
            classes="fill-height",
            #    style="width: 100%; height: 600px; border: none;"
        )

        html.Iframe(
            src="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
            classes="fill-height",
            style="width: 100%; height: 600px; border: none;",
        )

        html.Iframe(
            src="http://0.0.0.0:8000/?url=file:///home/zx5/1-todo/6-hardware/code/expgui/ExpHub/webpage.png",
            classes="fill-height",
            style="width: 100%; height: 600px; border: none;",
        )

        with vuetify.VTab(
            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
            raw_attrs=['''target="_blank"'''],
        ):
            html.Span("Instrument Status", classes="mr-1")
            vuetify.VIcon("mdi-open-in-new")
        # with GridLayout(columns=1):
        #    vuetify.VBtn("Open External CS-Studio page", click=self.open_webpage)

    # import webbrowser
    def open_webpage(self, *args: Any) -> None:
        pass
        # webbrowser.open("https://example.com")

    def create_ui_0(self) -> None:
        # with SinglePageLayout(server=self.server) as layout:
        #    layout.title.set_text("CSS Status")
        #    with layout.content:
        #        html.Div("This is the CSS Status page.")

        # html.Img(
        #        src="file:///home/zx5/1-todo/6-hardware/code/expgui/ExpHub/webpage.png",
        # )
        # html.Img(src="https://single-crystal.ornl.gov/_images/HB3A_Q.svg")
        screenshot = save_webpage_as_image(bl12cssstatus_urlsrc)

        from io import BytesIO

        import plotly.graph_objects as go
        from PIL import Image

        # Convert screenshot bytes to an image
        image = Image.open(BytesIO(screenshot))

        # Create a Plotly figure
        fig = go.Figure()

        # Add the image to the figure
        fig.add_layout_image(
            {
                "source": image,
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": 1,
                "sizex": 1,
                "sizey": 1,
                "xanchor": "left",
                "yanchor": "top",
            }
        )

        # Update layout to remove axes
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})

        # Render the figure
        # pio.show(fig)
        # with HBoxLayout(halign="center", height="50vh"):
        #    self.figure.update(fig)
        #    self.figure = plotly.Figure()
        from io import BytesIO

        # import matplotlib.image as mpimg
        import matplotlib.pyplot as plt

        # img = mpimg.imread(BytesIO(screenshot), format="png")
        fig, ax = plt.subplots()
        #        ax.imshow(img)

        with html.Div(classes="fill-width"):
            # Use VIframe to embed a webpage
            from io import BytesIO

            # import requests
            from PIL import Image

            # response = requests.get("https://sns.gov/about")
            # response = requests.get("https://www.sciencegateway.org/gr/morse.htm")
            # print(response.text)
            html.Iframe(
                src="https://single-crystal.ornl.gov/instruments/index.html",
                style="width: 100%; height: calc(100vh - 100px); border: none;",
            )
            html.Iframe(
                #    #srcdoc=response.text,
                #    #src="https://sns.gov/about",
                # src="https://single-crystal.ornl.gov/instruments/index.html",
                src="https://monitor.sns.gov/dasmon/",
                #    #src="https://www.sheldonbrown.com/web_sample1.html",
                #    #classes="fill-height",
            )
            # html.Div(
            #    """
            #    <iframe src="https://sns.gov/about" style="width: 100%; height: 600px; border: none;"></iframe>
            #    """,
            #    classes="fill-width"
            # )
            # html.Iframe(
            #    src="https://www.sciencegateway.org/gr/morse.htm",
            #    classes="fill-height",
            #    #style="width: 100%; height: calc(100vh - 100px); border: none;"
            #    style="width: 100%; height: calc(100vh - 100px); border: none;"
            # )
            save_webpage_as_image(bl12cssstatus_urlsrc)
            html.Iframe(
                src="file:///home/zx5/1-todo/6-hardware/code/expgui/ExpHub/webpage.png",
                #    classes="fill-height",
                #    style="width: 100%; height: calc(100vh - 100px); border: none;"
            )

            # html.Iframe(
            #    src="file:///home/zx5/1-todo/6-hardware/code/expgui/ExpHub/temp2.html",
            #    #src="https://www.sciencegateway.org/gr/morse.htm",
            #    classes="fill-height",
            #    style="width: 100%; height: calc(100vh - 100px); border: none;"
            # )
            # html.Iframe(
            #    src="https://example.com",
            #    classes="fill-height",
            #    #style="width: 100%; height: calc(100vh - 100px); border: none;"
            #    style="width: 100%; height: calc(100vh - 100px); border: none;"
            # )
            html.Iframe(
                src="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
                classes="fill-height",
                style="width: 100%; height: 600px; border: none;",
            )
        with vuetify.VTab(
            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
            raw_attrs=['''target="_blank"'''],
        ):
            html.Span("Instrument Status", classes="mr-1")
            vuetify.VIcon("mdi-open-in-new")
