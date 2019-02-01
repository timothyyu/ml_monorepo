from collections import OrderedDict

def figure_to_html(figure, prefix=None, max_in_a_row=None, true_break_between_rows=False):
    """ Turns filepaths to nice html-figures

    Parameters
    ----------
    figure: Union[List[str], str]
        path or list of paths
    prefix: Union[None, str]
        if set, the length of this string will be clipped from beginning
    max_in_a_row: Union[None, int]
        if set, insert a break after this many plots
    true_break_between_rows: bool
        if False, a siple <br> tag will be set between the rows, if True, will insert div-end tags

    Returns
    -------
    html: Union[str, List[str]
        html-code or list with independent html-codes
    """
    if not prefix:
        prefix = ""
    if not max_in_a_row or max_in_a_row > len(figure):
        max_in_a_row = len(figure)

    alternative_text = "Plot missing - is phantomjs installed? Check CAVEs FAQ for infos."

    div = "<div align=\"center\">\n"
    if not figure:
        return ""
    elif isinstance(figure, str):
        div += ("<a href=\"{0}\" data-lightbox=\"{0}\" "
                "data-title=\"{0}\"><img src=\"{0}\" alt=\"{1}\" "
                "width=\"600px\"></a>\n".format(figure[len(prefix):].lstrip("/"), alternative_text))
    else:
        # List with multiple figures size relative, put next to each other
        width = (100 - len(figure)) / len(figure)
        #width = (100 - max_in_a_row) / max_in_a_row
        counter = 0
        for fig in figure:
            if counter == max_in_a_row:
                if true_break_between_rows:
                    div += "<p style=\"clear: both;\">"
                    div += "</div>\n"
                    div += "<div align=\"center\">\n"
                else:
                    div += " <br> "
                counter = 0
            div += "<a href=\"{0}\" data-lightbox=\"{1}\" data-title=\"{0}\"><img src=\"{0}\"".format(
                                fig[len(prefix):].lstrip("/"), str(figure))
            div += " alt=\"{0}\" style=\"float: left; width: {1}%; margin-right: "\
                   "1%; margin-bottom: 0.5em;\"></a>\n".format(alternative_text, int(width))
            counter += 1
        div += "<p style=\"clear: both;\">"
    div += "</div>\n"
    return div

def _split_table(table: OrderedDict):
    """Splits an OrderedDict into a list of tuples that can be turned into a
    HTML-table with pandas DataFrame

    Parameters
    ----------
    table: OrderedDict
        table that is to be split into two columns

    Returns
    -------
    table_split: List[tuple(key, value, key, value)]
        list with two key-value pairs per entry that can be used by pandas
        df.to_html()
    """
    table_split = []
    keys = list(table.keys())
    half_size = len(keys) // 2
    for i in range(half_size):
        j = i + half_size
        table_split.append(("<b>" + keys[i] + "</b>", table[keys[i]],
                            "<b>" + keys[j] + "</b>", table[keys[j]]))
    if len(keys) % 2 == 1:
        table_split.append(("<b>"+keys[-1]+"</b>", table[keys[-1]], '', ''))
    return table_split

