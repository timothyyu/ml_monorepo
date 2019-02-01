from typing import List, Tuple

class BaseAnalyzer(object):

    def __init__(self, *args, **kwargs):
        self.plots = []

    def get_static_plots(self) -> List[str]:
        """ Returns plot-paths, if any are available

        Returns
        -------
        plot_paths: List[str]
            returns list of strings
        """
        raise NotImplementedError()

    def get_table(self):
        """ Get table, if available """
        raise NotImplementedError()

    def get_html(self) -> Tuple[str, str]:
        """General reports in html-format, to be easily integrated in html-code. ALSO FOR BOKEH-OUTPUT.

        Returns
        -------
        script, div: str, str
            header and body part of html-code
        """
        raise NotImplementedError()

    def get_jupyter(self):
        """Depending on analysis, this creates jupyter-notebook compatible output."""
        raise NotImplementedError()
