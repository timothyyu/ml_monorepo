import logging

from bokeh.models import (HoverTool, ColorBar, LinearColorMapper, BasicTicker, CustomJS, Slider,
                          ColumnDataSource)
from bokeh.models.widgets import (RadioButtonGroup, CheckboxButtonGroup, CheckboxGroup, Button, Select,
                                  DataTable, TableColumn)

def get_checkbox(glyph_renderers, labels):
    """
    Parameters
    ----------
    glyph_renderers: List[List[Renderer]]
        list of glyph-renderers
    labels: List[str]
        list with strings to be put in checkbox

    Returns
    -------
    checkbox: CheckboxGroup
        checkbox object
    select_all: Button
        button related to checkbox
    select_none: Button
        button related to checkbox
    """
    code, args_checkbox = _prepare_nested_glyphs(glyph_renderers)
    # Toggle all renderers in a subgroup, if their domain is set to active
    code += """
        for (i = 0; i < len_labels; i++) {
            if (cb_obj.active.includes(i)) {
                // console.log('Setting to true: ' + i + '(' + glyph_renderers[i].length + ')')
                for (j = 0; j < glyph_renderers[i].length; j++) {
                    glyph_renderers[i][j].visible = true;
                    // console.log('Setting to true: ' + i + ' : ' + j)
                }
            } else {
                // console.log('Setting to false: ' + i + '(' + glyph_renderers[i].length + ')')
                for (j = 0; j < glyph_renderers[i].length; j++) {
                    glyph_renderers[i][j].visible = false;
                    // console.log('Setting to false: ' + i + ' : ' + j)
                }
            }
        }
        """

    # Create the actual checkbox-widget
    callback = CustomJS(args=args_checkbox, code=code)
    checkbox = CheckboxButtonGroup(labels=labels, active=list(range(len(labels))), callback=callback)

    # Select all/none:
    handle_list_as_string = str(list(range(len(glyph_renderers))))
    code_button_tail = "checkbox.active = labels;" + code.replace('cb_obj', 'checkbox')
    select_all = Button(label="All", callback=CustomJS(args=dict({'checkbox':checkbox}, **args_checkbox),
                                                       code="var labels = {}; ".format(handle_list_as_string) + code_button_tail))
    select_none = Button(label="None", callback=CustomJS(args=dict({'checkbox':checkbox}, **args_checkbox),
                                                       code="var labels = {}; ".format('[]') + code_button_tail))

    return checkbox, select_all, select_none

def get_radiobuttongroup(glyph_renderers, labels):
    """
    Parameters
    ----------
    glyph_renderers: List[List[Renderer]]
        list of glyph-renderers
    labels: List[str]
        list with strings to be put in widget

    Returns
    -------
    radiobuttongroup: RadioButtonGroup
        radiobuttongroup widget to select one of the elements
    """
    code, args = _prepare_nested_glyphs(glyph_renderers)

    # Toggle all renderers in a subgroup, if their domain is set to active
    code += """
        for (i = 0; i < len_labels; i++) {
            if (cb_obj.active === i) {
                console.log('Setting to true: ' + i + '(' + glyph_renderers[i].length + ')')
                for (j = 0; j < glyph_renderers[i].length; j++) {
                    glyph_renderers[i][j].visible = true;
                    console.log('Setting to true: ' + i + ' : ' + j)
                }
            } else {
                console.log('Setting to false: ' + i + '(' + glyph_renderers[i].length + ')')
                for (j = 0; j < glyph_renderers[i].length; j++) {
                    glyph_renderers[i][j].visible = false;
                    console.log('Setting to false: ' + i + ' : ' + j)
                }
            }
        }
        """
    # Create the actual checkbox-widget
    callback = CustomJS(args=args, code=code)
    radio = RadioButtonGroup(labels=labels, active=0, callback=callback)
    return radio

def _prepare_nested_glyphs(glyph_renderers):
    # First create a consecutive list of strings named glyph_renderer_i for i in len(all_renderers)
    num_total_lines = sum([len(group) for group in glyph_renderers])
    aliases_flattened = ['glyph_renderer' + str(i) for i in range(num_total_lines)]
    # Make that list nested to sum up multiple renderers in one checkbox
    aliases = []
    start = 0
    for group in glyph_renderers:
        aliases.append(aliases_flattened[start: start+len(group)])
        start += len(group)
    # Flatten renderers-list to pass it to the CustomJS properly
    glyph_renderers_flattened = [a for b in glyph_renderers for a in b]
    args = {name: glyph for name, glyph in zip(aliases_flattened, glyph_renderers_flattened)}

    # Create javascript-code
    code = "len_labels = " + str(len(aliases)) + ";"
    # Create nested list of glyph renderers to be toggled by a button
    code += "glyph_renderers = [" + ','.join(['[' + ','.join([str(idx) for idx in group]) + ']' for group in aliases]) + '];'
    return code, args

def array_to_bokeh_table(df, sortable=None, width=None, logger=None):
    """
    Create bokeh-table from array.

    Parameters
    ----------
    array: pandas.DataFrame
        dataframe with columns and index set
    sortable: dict(str : boolean)
        columns that should be sortable, default none
    width: dict(str : int)
        width of columns, default 100 for all
    logger: logging.Logger
        logger to use, if not set use default

    Returns
    -------
    bokeh_table: bokeh.models.widgets.DataTable
        bokeh object
    """
    if logger is None:
        logger = logging.getLogger('cave.utils.bokeh_routines.array_to_bokeh_table')
    if sortable is None:
        sortable = {}
    if width is None:
        width = {}

    columns = list(df.columns.values)
    data = dict(df[columns])

    # Sanity checks
    for attr, d in {'width' : width, 'sortable' : sortable}.items():
        diff = set(d.keys()).difference(set(columns))
        if len(diff) > 0:
            logger.debug("For attr %s with value %s and columns %s there is a diff %s", attr, d, columns, diff)
            raise ValueError("Illegal table description! Trying to specify '%s' for the following columns, but they "
                             "are not present in DataFrame: %s!" % (attr, diff))

    source = ColumnDataSource(data)
    columns = [TableColumn(field=header, title=header,
                           sortable=sortable.get(header, False),
                           default_sort='descending',
                           width=width.get(header, 100)) for header in columns
              ]
    data_table = DataTable(source=source,
                           columns=columns,
                           height=20 + 30 * len(list(data.values())[0]),
                           index_position=None,  # Disable index-column
                           )
    return data_table
