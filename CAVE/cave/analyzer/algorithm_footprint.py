import os
from collections import OrderedDict
import logging

from bokeh.plotting import show
from bokeh.io import output_notebook
from bokeh.embed import components

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.plot.algorithm_footprint import AlgorithmFootprintPlotter
from cave.utils.timing import timing

class AlgorithmFootprint(BaseAnalyzer):

    @timing
    def __init__(self, algorithms, epm_rh, train, test, features,
                 cutoff, output_dir, rng, density=200, purity=0.95):
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        # filter instance features
        train_feats = {k: v for k, v in features.items() if k in train}
        test_feats = {k: v for k, v in features.items() if k in test}
        if not (train_feats or test_feats):
            self.logger.warning("No instance-features could be detected. "
                                "No algorithm footprints available.")
            raise ValueError("Could not detect any instances.")

        self.logger.info("... algorithm footprints for: {}".format(",".join([a[1] for a in algorithms])))
        self.footprint = AlgorithmFootprintPlotter(epm_rh,
                                              train_feats, test_feats,
                                              algorithms,
                                              cutoff,
                                              output_dir,
                                              rng=rng)

    def _plot(self):
        # Plot footprints
        bokeh_plot = self.footprint.plot_interactive_footprint()
        self.plots3d = self.footprint.plot3d()
        return bokeh_plot

    def get_jupyter(self):
        bokeh_plot = self._plot()
        output_notebook()
        show(bokeh_plot)

    def get_html(self, d=None, tooltip=None):
        script, div = components(self._plot())
        bokeh_components = script, div
        if d is not None:
            d["tooltip"] = tooltip
            # Interactive bokeh-plot
            d["Interactive Algorithm Footprint"] = {"bokeh" : (script, div)}
            for plots in self.plots3d:
                header = os.path.splitext(os.path.split(plots[0])[1])[0][10:-2]
                header = header[0].upper() + header[1:].replace('_', ' ')
                d[header] = {"figure_x2": plots}

        return bokeh_components

    def get_plots(self):
        all_plots = []
        for plots in self.plots3d:
            all_plots.extend(plots)
        return all_plots
