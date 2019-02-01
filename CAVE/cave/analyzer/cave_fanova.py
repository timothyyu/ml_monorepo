import os
from collections import OrderedDict
import operator
import logging

from pandas import DataFrame

from cave.analyzer.cave_parameter_importance import CaveParameterImportance
from cave.html.html_helpers import figure_to_html

class CaveFanova(CaveParameterImportance):

    def __init__(self,
                 pimp,
                 incumbent,
                 output_dir,
                 marginal_threshold=0.05):
        """Wrapper for parameter_importance to save the importance-object/
        extract the results. We want to show the top X most important
        parameter-fanova-plots.

        Parameters
        ----------
        pimp: Importance
            parameter importance object
        incumbent: Configuration
            incumbent configuration
        marginal_threshold: float
            parameter/s must be at least this important to be mentioned
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        super().__init__(pimp, incumbent, output_dir)

        # To be set
        self.fanova_table = None
        self.single_plots = {}
        self.pairwise_plots = {}
        self.error = ""

        def parse_pairwise(p):
            """parse pimp's way of having pairwise parameters as key as str and return list of individuals"""
            res = [tmp.strip('\' ') for tmp in p.strip('[]').split(',')]
            return res

        try:
            self.parameter_importance("fanova")
        except RuntimeError as e:
            err = "Encountered error '%s' in fANOVA, this can e.g. happen with too few data-points." % e
            self.logger.info(err, exc_info=1)
            self.error = err
            return
        parameter_imp = {k: v * 100 for k, v in self.pimp.evaluator.evaluated_parameter_importance.items()}
        parameter_imp_std = {}
        # TODO Following is only available for install from master-branch (pimp and fanova)
        if hasattr(self.pimp.evaluator, 'evaluated_parameter_importance_uncertainty'):
            parameter_imp_std = {k: v * 100 for k, v in pimp.evaluator.evaluated_parameter_importance_uncertainty.items()}

        for k in parameter_imp.keys():
            self.logger.debug("fanova-importance for %s: mean (over trees): %f, std: %s", k, parameter_imp[k],
                              str(parameter_imp_std[k]) if parameter_imp_std else 'N/A')

        # Split single and pairwise (pairwise are string: "['p1','p2']")
        single_imp = {k : v for k, v in parameter_imp.items() if not k.startswith('[') and v > marginal_threshold}
        pairwise_imp = {k : v for k, v in parameter_imp.items() if k.startswith('[') and v > marginal_threshold}

        # Set internal parameter importance for further analysis (such as parallel coordinates)
        self.param_imp['fanova'] = single_imp

        # Dicts to lists of tuples, sorted descending after importance
        single_imp = OrderedDict(sorted(single_imp.items(), key=operator.itemgetter(1), reverse=True))
        pairwise_imp = OrderedDict(sorted(pairwise_imp.items(), key=operator.itemgetter(1), reverse=True))

        # Create table
        table = []
        if len(single_imp) > 0:
            table.extend([(20*"-"+" Single importance: "+20*"-", 20*"-")])
            for k, v in single_imp.items():
                value = str(round(v, 4))
                if parameter_imp_std:
                    value += " +/- " + str(round(parameter_imp_std[k], 4))
                table.append((k, value))
        if len(pairwise_imp) > 0:
            table.extend([(20*"-"+" Pairwise importance: "+20*"-", 20*"-")])
            for k, v in pairwise_imp.items():
                name = ' & '.join(parse_pairwise(k))
                value = str(round(v, 4))
                if parameter_imp_std:
                    value += " +/- " + str(round(parameter_imp_std[k], 4))
                table.append((name, value))

        keys, fanova_table = [k[0] for k in table], [k[1:] for k in table]
        df = DataFrame(data=fanova_table, index=keys)
        self.fanova_table = df.to_html(escape=False, header=False, index=True, justify='left')

        # Get plot-paths
        self.single_plots = {p : os.path.join(self.output_dir, "fanova", p + '.png') for p in single_imp.keys()}
        # Right now no way to access paths of the plots -> file issue
        self.pairwise_plots = {" & ".join(parse_pairwise(k)) : os.path.join(self.output_dir, 'fanova', '_'.join(parse_pairwise(k)) + '.png') for p in pairwise_imp.keys()}
        self.pairwise_plots = {p : path for p, path in self.pairwise_plots.items() if os.path.exists(path)}

    def get_table(self):
        return self.fanova_table

    def get_plots(self):
        return list(self.single_plots.values()) + list(self.pairwise_plots.values())

    def get_html(self, d=None, tooltip=None):
        div = ""
        if d is not None and self.error:
            d["else"] = self.error + " Check 'debug/debug.log' for more information."
            div = self.error
        elif d is not None:
            d["tooltip"] = tooltip
            d["Importance"] = {"table": self.fanova_table}
            # Insert plots (the received plots is a dict, mapping param -> path)
            d["Marginals"] = OrderedDict()
            for param, plot in self.single_plots.items():
                d["Marginals"][param] = {"figure": plot}
            if self.pairwise_plots:
                d["Pairwise Marginals"] = OrderedDict()
                for param, plot in self.pairwise_plots.items():
                    d["Pairwise Marginals"][param] = {"figure": plot}

        return "", div

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        # Show table
        display(HTML(self.get_table()))
        # Show plots
        display(HTML(figure_to_html(list(self.single_plots.values()) + list(self.pairwise_plots.values()), max_in_a_row=3, true_break_between_rows=True)))

