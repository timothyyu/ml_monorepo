from scipy.stats import ttest_rel


def paired_permutation(data1, data2, rng, num_permutations=10000, logger=None):
    """Test for significance using paired permutation.

    Parameters
    ----------
    data1, data2: List<float>, List<float>
        ordered results for instances for two different configurations
    rng: np.RandomState
        random number generator
    num_permutations: int
        number of permutations performed
    logger: Logger
        logger-instance write debugs to

    Returns
    -------
    p: float
        p-value for statistical test
    """
    assert(len(data1) == len(data2))

    def test(x, y):
        """Mean of difference between two lists of results"""
        return abs((sum(x) / float(len(x))) - (sum(y) / float(len(y))))
    # Original order
    t = test(data1, data2)
    # Test-statistics for 10000 permutations of data in s
    s = [t]
    for count in range(num_permutations):
        # Shuffle data
        X, Y = zip(*[rng.permutation([d1, d2]) for d1, d2 in zip(data1, data2)])
        s.append(test(X, Y))
    # Find p-value
    larger = len([z for z in s if z >= t])
    p = larger / float(len(s))
    if logger:
        logger.debug("Permutation test with %d/%d permutations yielding a "
                     "higher mean of difference between permutated data than "
                     "the real data (%f), yielding a p-value of %f",
                     larger, len(s), t, p)
    return p


def paired_t_student(data1, data2, logger=None):
    """Test for significance using paired t-test.

    Parameters
    ----------
    data1, data2: List<float>, List<float>
        ordered results for instances for two different configurations
    logger: logging.Logger
        to log scores, if given

    Returns
    -------
    p: float
        p-value for statistical test
    """
    t, p = ttest_rel(data1, data2)
    if logger:
        logger.debug("Paired t-test with %d samples yields t-value of %f and "
                     "p-value of %f", len(data1), t, p)
    return p
