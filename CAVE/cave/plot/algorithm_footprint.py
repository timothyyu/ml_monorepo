import os
import logging
import time
from collections import OrderedDict
import itertools

import numpy as np
import matplotlib.pyplot as plt
plt.style.use(os.path.join(os.path.dirname(__file__), 'mpl_style'))  # noqa
from scipy import spatial
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models import HoverTool, CustomJS, CDSView, GroupFilter
from bokeh.models.widgets import RadioButtonGroup
from bokeh.models.ranges import DataRange1d
from bokeh.layouts import row, column, widgetbox

from smac.runhistory.runhistory import RunHistory

from cave.utils.helpers import get_cost_dict_for_config
from cave.utils.io import export_bokeh

__author__ = "Joshua Marben"
__copyright__ = "Copyright 2017, ML4AAD"
__license__ = "3-clause BSD"
__maintainer__ = "Joshua Marben"
__email__ = "jo.ma@posteo.de"


class AlgorithmFootprintPlotter(object):
    """ Class that provides the algorithmic footprints after
    "Measuring algorithm footprints in instance space"
    (Kate Smith-Miles, Kate Smith-Miles)

    General procedure:
        - label for each algorithm each instance with the same metric
        - map the instances onto a plane using pca

    NOTE:
    The terms 'algorithm' and 'config/configuration' will be used synonymous
    throughout the class.
    """
    def __init__(self,
                 rh: RunHistory,
                 train_inst_feat,
                 test_inst_feat,
                 algorithms,
                 cutoff=np.inf,
                 output_dir=None,
                 rng=None):
        """
        Parameters
        ----------
        rh: RunHistory
            runhistory to take cost from
        train_inst_feat, test_inst_feat: dict[str->np.array]
            instances names mapped to features
        algorithms: List[Tuple(Configuration, str)]
            list with configs and descriptive names
        cutoff: int
            cutoff (if available)
        output_dir: str
            output directory
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        self.output_dir = output_dir
        self.rng = rng
        if not self.rng:
            self.logger.debug("No randomstate passed. Generate deterministic random state.")
            self.rng = np.random.RandomState(42)

        self.rh = rh
        self.train_feats = train_inst_feat
        self.test_feats = test_inst_feat
        self.inst_to_feat = {**train_inst_feat, **test_inst_feat}
        # This is the order of instances:
        self.insts = list(train_inst_feat.keys()) + list(test_inst_feat.keys())
        if self.output_dir and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.algorithms = [config for config, name in algorithms]    # Configuration-objects
        self.algo_name = {algo: name for algo, name in algorithms}  # Mapping config to name
        self.name_algo = {name: algo for algo, name in algorithms}  # and vice versa
        if len(self.algo_name.keys()) < len(self.name_algo.keys()):
            raise ValueError("Default and Incumbent are equal or some other error occured. Deactivate "
                             "algorithm-footprints with --no_algorithm_footprint")

        self.algo_labels = {}  # Maps algo -> label (good and bad)

        self.features = np.array([self.inst_to_feat[k] for k in self.insts])
        self.features_2d = self._reduce_dim(self.features, 2)
        self.features_3d = self._reduce_dim(self.features, 3)
        # self.clusters, self.cluster_dict = self.get_clusters(self.features_2d)

        self.cutoff = cutoff

        self._label_instances()

    def _reduce_dim(self, feature_array, n=2):
        """ Expects feature-array (not dict!), performs a PCA

        Parameters
        ----------
        feature_array: np.array
            array containing features in order of self.inst_names
        n: int
            target dimension for pca, 2 or 3

        Returns
        -------
        feature_array_nd: np.array
            array with pca'ed features (n-dimensional)
        """
        if n not in [2, 3]:
            raise ValueError("Only 2 and 3 supported as target dimension!")
        if feature_array.shape[1] > n:
            self.logger.debug("Use PCA to reduce features to %d dimensions", n)
            feature_array = StandardScaler().fit_transform(feature_array)
            feature_array = PCA(n_components=n).fit_transform(feature_array)
        return feature_array

    def _get_cost(self, algorithm, instance=None):
        """
        Return cost according to (possibly EPM-)validated runhistory.

        Parameters
        ----------
        algorithm: Configuration
            config
        instance: str
            instance name
        """
        if not hasattr(self, '__algo_cost'):
            self.__algo_cost = {}  # Use function self._get_cost!! Maps algo -> {instance -> cost}
        if algorithm not in self.__algo_cost:
            #self.logger.debug("Getting cost for %s, using PAR1-score", self.algo_name[algorithm])
            self.__algo_cost[algorithm] = get_cost_dict_for_config(self.rh, algorithm)
        if instance:
            return self.__algo_cost[algorithm][instance]
        else:
            return self.__algo_cost[algorithm]

    def _label_instances(self, epsilon=0.95):
        """
        Returns dictionary with a label for each instance.

        Returns
        -------
        labels: Dict[str:float]
            maps instance-names (strings) to label (floats)
        """
        start = time.time()
        if len(self.algo_labels) > 0:
            return
        self.algo_labels = {a: {} for a in self.algo_name.keys()}
        for i in self.insts:
            best_cost = min([self._get_cost(a, i) for a in self.algo_name.keys()])
            for a in self.algo_name.keys():
                cost = self._get_cost(a, i)
                # self.logger.debug("%s on \'%s\': best/this (%f/%f=%f)",
                #                  self.algo_name[a], i,
                #                  best_cost, cost,
                #                  best_cost / cost)
                if (cost == 0 or
                    (best_cost/cost >= epsilon and
                     (not self.cutoff or not cost >= self.cutoff))):
                    # Algorithm for instance is in threshhold epsilon and no timeout
                    label = 1
                else:
                    label = 0
                self.algo_labels[a][i] = label
        self.logger.debug("Labeling instances in %.2f secs.", time.time() - start)

# -~-~-~-~ FOOTPRINT

    def footprint(self, a, density_threshold, purity_threshold):
        """
        Calculating the footprint within a portfolio using convex hulls that
        depend on density and purity thresholds.
        (algorithm 1 in Smith-Miles 2014)

        We use 3 ways to refer to an instance here:
        name: the name (unique!) of the instance
        feat2d: the position as np.array
        tup: the tuple-version of feat2d (hashable...)

        Parameters
        ----------
        a: Configuration
            configuration to get footprint of
        density_threshold: float
            minimum density that regions must show to be merged
        purity_threshold: float
            minimum purity (percentage of good instance)
            that regions must show to be merged

        Returns
        -------
        footprint: float
            the size of all resulting convex hulls
        """
        def get_2NN(x, X):
            """ Return indices in X of two nearest points in X to x. """
            # map index to dist from point
            dist = [(i, np.linalg.norm(tmp - x)) for i, tmp in enumerate(X)]
            # sort after dist
            dist = sorted(dist, key=lambda x: x[1])
            # return indices of the two smallest values
            return (dist[0][0], dist[1][0])

        count_exceptions = 0

        # -~-~ Initialise Stage
        # Map inst-names to feat2d (np.array) and tup (tuple)
        inst_feat2d = {i: self.features_2d[idx] for idx, i in enumerate(self.insts)}
        inst_tup = {i: tuple(pos) for i, pos in inst_feat2d.items()}  # noqa

        # regions maps tuple(centroid) of region to inst-names in region
        regions = OrderedDict()

        # Instances (by name) in not_in_region
        not_in_region = self.insts[:]

        # Randomly select a good instance;
        good = [i for i in self.insts if self.algo_labels[a][i] == 1]
        if len(good) < 3:
            self.logger.debug("Less than 3 good instances found in %s, footprint"
                              " not calculated.", self.algo_name[a])
            return 0

        # Repeat until no more triangles can be formed (at least 3 points left).
        while (len(not_in_region) >= 3):
            # Select random good instance TODO also from in_regions?!?!
            rand_good = self.rng.choice(good)
            try:
                not_in_region.remove(rand_good)  # Remove here so it's not its own nearest neighbor
            except ValueError:
                pass

            # Form a closed region (triangle) with the two closest (smallest
            #        Euclidean distance in feature space) instances to
            #        rand_good, not already part of a triangle;
            idx1, idx2 = get_2NN(inst_feat2d[rand_good],
                                 [inst_feat2d[i] for i in not_in_region])

            triangle = (rand_good, not_in_region[idx1], not_in_region[idx2])  # names
            triangle_feat = np.array([inst_feat2d[i] for i in triangle])
            centroid = np.sum(np.array(triangle_feat), axis=0)/len(triangle)
            regions[tuple(centroid)] = triangle
            for p in triangle:
                try:
                    not_in_region.remove(p)
                except ValueError:
                    pass

        # -~-~ Merge Stage
        # Repeat the Merge Stage until there are no more pairs to consider.
        # If we iterated over whole list once, we are done.
        stop = False
        while not stop:
            stop = True
            centroids = list(regions.keys())
            self.rng.shuffle(centroids)
            # Randomly select a closed region;
            for idx, cent in enumerate(centroids):
                reg = regions[cent]          # inst-names!
                cent_array = np.array(cent)  # Keys in dict are tuples!

                # Find the closest closed region (minimum Euclidean
                #   centroid distance);
                remaining_centroids = [np.array(c) for c in regions.keys() if not c == cent]
                idx = get_2NN(cent_array, remaining_centroids)[0]
                nearest_cent = tuple(remaining_centroids[idx])
                nearest_reg = regions[nearest_cent]  # inst-names!

                # Check purity and density
                new_reg = tuple(set(reg) | set(nearest_reg))  # names
                new_reg_array = np.array([inst_feat2d[i] for i in new_reg])  # array
                try:
                    combined_hull = spatial.ConvexHull(new_reg_array)
                except spatial.qhull.QhullError:
                    count_exceptions += 1
                    continue
                density = len(new_reg)/combined_hull.volume
                purity = (len([i for i in reg if i in good]) +
                          len([i for i in nearest_reg if i in good])) / float(len(new_reg))
                if density > density_threshold and purity > purity_threshold:
                    self.logger.debug("Purity: %f, density: %f", purity, density)
                    regions.pop(cent)
                    regions.pop(nearest_cent)
                    new_centroid = tuple(np.sum(new_reg_array, axis=0)/len(new_reg))
                    regions[new_centroid] = new_reg
                    stop = False
                    break

        # We now have final regions -> return sum of individual convex hulls
        area = 0
        for reg in regions.values():
            try:
                hull = spatial.ConvexHull(np.array([inst_feat2d[p] for p in reg]))
                area += hull.volume
            except spatial.qhull.QhullError:
                count_exceptions += 1
                pass
        self.logger.debug("Area for %s is %f (%d Qhull-exceptions, %d/%d good "
                          "insts, %d regions)",
                          self.algo_name[a], area, count_exceptions, len(good),
                          len(self.insts), len(regions))
        return area

# -~-~-~ PLOTS
    def _get_good_bad(self, conf, insts=[]):
        """ Creates a list of indices for good and bad instances for a
        configuration.

        Parameters
        ----------
        conf: Configuration
            configuration for which to plot good vs bad
        insts: List[str]
            instances to be plotted

        Returns
        -------
        outpath: str
            output path
        """
        if len(insts) == 0:
            insts = self.insts

        good_idx, bad_idx = [], []
        for k, v in self._get_cost(conf).items():
            # Only consider passed insts
            if k not in insts:
                continue
            # Append inst-idx either to good or to bad
            if self.algo_labels[conf][k] == 0:
                bad_idx.append(self.insts.index(k))
            else:
                good_idx.append(self.insts.index(k))
        assert(len(good_idx) == len(set(good_idx)))
        assert(len(bad_idx) == len(set(bad_idx)))
        good_idx, bad_idx = np.array(good_idx), np.array(bad_idx)
        self.logger.debug("for config %s good: %d, bad: %d",
                          self.algo_name[conf], len(good_idx), len(bad_idx))
        return (good_idx, bad_idx)

    def plot_interactive_footprint(self):
        """Use bokeh to create an interactive algorithm footprint with zoom and
        hover tooltips. Should avoid problems with overplotting (since we can
        zoom) and provide better information about instances."""
        features = np.array(self.features_2d)
        instances = self.insts
        runhistory = self.rh
        algo = {v: k for k, v in self.algo_name.items()}
        incumbent = algo['incumbent']
        default = algo['default']
        source = ColumnDataSource(data=dict(x=features[:, 0], y=features[:, 1]))
        # Add all necessary information for incumbent and default
        source.add(instances, 'instance_name')
        instance_set = ['train' if i in self.train_feats.keys() else 'test' for i in instances]
        source.add(instance_set, 'instance_set')  # train or test
        for config, name in [(incumbent, 'incumbent'), (default, 'default')]:
            cost = get_cost_dict_for_config(runhistory, config)
            source.add([cost[i] for i in instances], '{}_cost'.format(name))
            # TODO should be in function
            good, bad = self._get_good_bad(config)
            color = [1 if idx in good else 0 for idx, i in enumerate(instances)]
            # TODO end
            color = ['blue' if c else 'red' for c in color]
            self.logger.debug("%s colors: %s", name, str(color))
            source.add(color, '{}_color'.format(name))
        source.add(source.data['default_color'], 'color')

        # Define what appears in tooltips
        hover = HoverTool(tooltips=[('instance name', '@instance_name'),
                                    ('def cost', '@default_cost'),
                                    ('inc_cost', '@incumbent_cost'),
                                    ('set', '@instance_set'),
                                    ])

        # Add radio-button
        def_inc_callback = CustomJS(args=dict(source=source), code="""
            var data = source.data;
            if (cb_obj.active == 0) {
                data['color'] = data['default_color'];
            } else {
                data['color'] = data['incumbent_color'];
            }
            source.change.emit();
            """)

        def_inc_radio_button = RadioButtonGroup(
                labels=["default", "incumbent"], active=0,
                callback=def_inc_callback)

        # Plot
        x_range = DataRange1d(bounds='auto', start=min(features[:, 0]) - 1, end=max(features[:, 0]) + 1)
        y_range = DataRange1d(bounds='auto', start=min(features[:, 1]) - 1, end=max(features[:, 1]) + 1)
        p = figure(plot_height=500, plot_width=600,
                   tools=[hover, 'save', 'wheel_zoom', 'box_zoom', 'pan', 'reset'], active_drag='box_zoom',
                   x_range=x_range, y_range=y_range)
        # Scatter train and test individually to toggle them
        train_view = CDSView(source=source, filters=[GroupFilter(column_name='instance_set', group='train')])
        test_view = CDSView(source=source, filters=[GroupFilter(column_name='instance_set', group='test')])
        train = p.scatter(x='x', y='y', source=source, view=train_view, color='color')
        test = p.scatter(x='x', y='y', source=source, view=test_view, color='color')
        p.xaxis.axis_label, p.yaxis.axis_label = 'principal component 1', 'principal component 2'
        p.xaxis.axis_label_text_font_size = p.yaxis.axis_label_text_font_size = "15pt"

        train_test_callback = CustomJS(args=dict(source=source, train_view=train, test_view=test), code="""
            var data = source.data;
            if (cb_obj.active == 0) {
                train_view.visible = true;
                test_view.visible = true;
            } else if (cb_obj.active == 1) {
                train_view.visible = true;
                test_view.visible = false;
            } else {
                train_view.visible = false;
                test_view.visible = true;
            }
            """)
        train_test_radio_button = RadioButtonGroup(
                labels=["all", "train", "test"], active=0,
                callback=train_test_callback)

        # Export and return
        if self.output_dir:
            path = os.path.join(self.output_dir, "content/images/algorithm_footprint.png")
            export_bokeh(p, path, self.logger)

        layout = column(p, row(widgetbox(def_inc_radio_button), widgetbox(train_test_radio_button)))
        return layout

    def plot3d(self):
        """ Plot 3d-version of the algorithm footprint from four different
        angles. """
        plots = []
        for a in self.algorithms:
            # Plot without clustering (for all insts)
            out_fns = [os.path.join(self.output_dir, 'footprint_' +
                       self.algo_name[a] + '_3d_{}.png'.format(i)) for i in range(4)]
            self.logger.debug("Plot saved to '%s'", out_fns)
            fig, ax = plt.subplots()
            good_idx, bad_idx = self._get_good_bad(a)
            good = np.array([self.features_3d[idx] for idx in good_idx])
            bad = np.array([self.features_3d[idx] for idx in bad_idx])
            axes = {0: 'principal component 1',
                    1: 'principal component 2',
                    2: 'principal component 3'}
            for out_fn, axes_ordered in zip(out_fns, list(itertools.permutations([0, 1, 2]))[:len(out_fns)]):
                # Plot 3d
                fig = plt.figure()
                ax = fig.add_subplot(111, projection='3d')
                x, y, z = axes_ordered
                if len(good) > 0:
                    ax.scatter(xs=good[:, x], ys=good[:, y], zs=good[:, z], color="blue")
                if len(bad) > 0:
                    ax.scatter(xs=bad[:, x], ys=bad[:, y], zs=bad[:, z], color="red")
                ax.set_xlabel(axes[x], fontsize=12)
                ax.set_ylabel(axes[y], fontsize=12)
                ax.set_zlabel(axes[z], fontsize=12)
                plt.tight_layout()
                # for out_fn, angle in zip(out_fns, range(20, 381, 90)):
                #     ax.view_init(30, angle)
                fig.savefig(out_fn)
                plt.close(fig)
            plots.append(out_fns)
        return plots

# -~-~- CLUSTER

    def plot_points_per_cluster(self):
        """ Plot good versus bad for passed config per cluster.

        Parameters
        ----------
        conf: Configuration
            configuration for which to plot good vs bad
        out: str
            output path

        Returns
        -------
        outpaths: List[str]
            output paths per cluster
        """
        # For Development/Debug:
        algo_fp_debug = os.path.join(self.output_dir, 'debug', 'algo_fp')
        if not os.path.exists(algo_fp_debug):
            os.makedirs(algo_fp_debug)
        for e in np.hstack([np.arange(0.0, 1.0, .95), np.arange(0.96, 1.0, 0.02)]):
            self._label_instances(e)
            for a in self.algorithms:
                # Plot without clustering (for all insts)
                suffix = 'all_{:4.3f}.png'.format(e)
                path = os.path.join(algo_fp_debug,
                                    '_'.join([self.algo_name[a], suffix]))
                path = self.plot2d(a, path)
                self.logger.debug("Plot saved to '%s'", path)
        self._label_instances()
        for c in self.cluster_dict.keys():
            # Plot per cluster
            path = os.path.join(algo_fp_debug, 'cluster_' + str(c) + '_fp_' +
                                               self.algo_name[a] + '_0.95.png')
            path = self.plot2d(a, path, self.cluster_dict[c])

    def get_clusters(self, features_2d):
        """ Mapping instances to clusters, using silhouette-scores to determine
        number of cluster.

        Returns
        -------
        paths: List[str]
            paths to plots
        """
        # get silhouette scores for k_means with 2 to 12 clusters
        # use number of clusters with highest silhouette score
        best_score, best_n_clusters = -1, -1
        min_clusters, max_clusters = 2, min(features_2d.shape[0], 12)
        clusters = None
        for n_clusters in range(min_clusters, max_clusters):
            km = KMeans(n_clusters=n_clusters)
            y_pred = km.fit_predict(features_2d)
            score = silhouette_score(features_2d, y_pred)
            if score > best_score:
                best_n_clusters = n_clusters
                best_score = score
                clusters = y_pred

        self.logger.debug("%d clusters detected using silhouette scores",
                          best_n_clusters)

        cluster_dict = {n: [] for n in range(best_n_clusters)}
        for i, c in enumerate(clusters):
            cluster_dict[c].append(self.insts[i])

        self.logger.debug("Distribution over clusters: %s",
                          str({k: len(v) for k, v in cluster_dict.items()}))

        return clusters, cluster_dict
