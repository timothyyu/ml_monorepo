def get_tooltip(header):
    tooltips = {
        "Performance Analysis": """
Contains different ways of analyzing
the final incumbent and the performance of
the algorithm's default parameter
configuration.""",

        "Default 3d": """
Projection of feature space into three dimensions, different viewpoints for
enhanced explanation.""",

        "Incumbent 3d": """
Projection of feature space into three dimensions,
different viewpoints for enhanced explanation.""",

        "Configurator's behavior": """
Analysis of the trajectory and the
runhistory returned by a configurator
to gain insights into how the configurator
tried to find a well-performing
configuration.""",

        "Parameter Importance": """
Parameter Importance analysis to determine
which of the parameters most influence the
analysed algorithms performance.""",

        "Feature Analysis": """
Analysis of the instance features to gain
insights into the instance set that
was used during the optimization.""",


        "Feature Importance": """
Reduction of the out-of-the-bag root
mean squared error of the random
forest empirical performance model
by applying forward selection on the set of
instance features. Using this method, we can
identify a set of instance features that
suffices to obtain prediction accuracy
comparable to using the full set of
features.""",
               }

    if header in tooltips:
        return tooltips[header]
    else:
        return False
