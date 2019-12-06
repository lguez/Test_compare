import numpy as np
from matplotlib import pyplot as plt, dates, ticker, cm, colors
import string
from itertools import cycle
from mpl_toolkits import basemap

def find_idx_nearest_val(array, value):
    """Find index of nearest value in a one-dimensional monotonous array."""

    n = len(array)

    if array[0] <= array[-1]:
        sorted_array = array
        index = range(n)
    else:
        sorted_array = array[::- 1]
        index = range(n - 1, - 1, - 1)

    i = np.searchsorted(sorted_array, value)

    if i == n:
        return index[n - 1]
    elif i == 0:
        return index[0]
    else:
        if abs(value - sorted_array[i - 1]) < abs(value - sorted_array[i]):
            return index[i-1]
        else:
            return index[i]

def step(x, y, **kwargs):
    l = plt.step(x[:-1], y, where = "post", **kwargs)
    color = l[0].get_color()
    plt.hlines(y[-1], x[-2], x[-1], color = color)

def draw_bbox(xmin, xmax, ymin, ymax, colors = "k", label = ""):
    plt.hlines([ymin, ymax], xmin, xmax, colors = colors, label = label)
    plt.vlines([xmin, xmax], ymin, ymax, colors = colors)

def read_line_array(filename):
    """Read one real array per line from a text file.

    We assume that the first two token of each line are the name of
    the array and the equal sign. The arrays on different lines do not
    have to have the same length. The function returns a dictionary of
    Numpy arrays. The keys are the names of the arrays.
    """

    my_dict = {}

    with open(filename) as f:
        for line in f:
            splitted_line = line.split()
            value_list = [float(token) for token in splitted_line[2:]]
            my_dict[splitted_line[0]] = np.array(value_list)

    return my_dict

def read_line_with_header(filename):
    """Read one real array per line from a text file.

    We assume that the first token of each line is a quoted header,
    which can contain white space. The arrays on different lines do
    not have to have the same length. The function returns a
    dictionary of Numpy arrays. The keys are the headers.

    """

    import csv

    my_dict = {}

    with open(filename) as f:
        reader = csv.reader(f, delimiter = " ", skipinitialspace = True, 
                            quoting = csv.QUOTE_NONNUMERIC)

        for line in reader:
            if line[-1] == "":
                # (white space at the end of the input line has
                # produced an empty string list item)
                del line[-1]

            my_dict[line[0]] = np.array(line[1:])

    return my_dict

def label_axes(fig, labels=None, loc=None, **kwargs):
    """
    Walks through axes and labels each.

    kwargs are collected and passed to `annotate`

    Parameters
    ----------
    fig : Figure
         Figure object to work on

    labels : iterable or None
        iterable of strings to use to label the axes.
        If None, lower case letters are used.

    loc : len=2 tuple of floats
        Where to put the label in axes-fraction units
    """
    if labels is None:
        labels = string.ascii_lowercase
        
    # re-use labels rather than stop labeling
    labels = cycle(labels)
    if loc is None:
        loc = (.9, .9)
    for ax, lab in zip(fig.axes, labels):
        ax.annotate(lab, xy=loc,
                    xycoords='axes fraction',
                    **kwargs)

def xlabel_months(ax):
    ax.xaxis.set_major_locator(dates.MonthLocator())
    ax.xaxis.set_minor_locator(dates.MonthLocator(bymonthday=15))

    ax.xaxis.set_major_formatter(ticker.NullFormatter())
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%b'))

    for tick in ax.xaxis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment('center')

def edge(x):
    """Returns an array with elements halfway between input values, plus
    edge values.

    x should be a numpy array. Useful for pcolormesh if available
    coordinates are at z points.

    """

    return np.insert((x[:-1] + x[1:]) / 2, (0, x.size - 1),
                     ((3 * x[0] - x[1]) / 2, (3 * x[- 1] - x[- 2]) / 2))

class Domain:
    def __init__(self, lon, lat, projection = "robin", lon_0 = - 155):
        lon_edg = edge(lon)
        lat_edg = edge(lat)
        lat_edg[0]=90
        lat_edg[-1]=-90
        self.m = basemap.Basemap(projection = projection, lon_0 = lon_0)
        self.lon_edg_mesh, self.lat_edg_mesh = np.meshgrid(lon_edg[1:], lat_edg)
    
    def shade(self, field, levels = None, cmap = cm.viridis):
        """field and levels should be numpy arrays."""

        if levels is None:
            level_min = field.min()
            level_max = field.max()
            levels = ticker.MaxNLocator(nbins = 5).tick_values(level_min, 
                                                               level_max)

        norm = colors.BoundaryNorm(levels, cmap.N)
        plt.figure(figsize = (10, 4.8))
        self.m.pcolormesh(self.lon_edg_mesh, self.lat_edg_mesh,
                                field[:, 1:], latlon=True, norm = norm,
                                cmap = cmap)
        my_colorbar = self.m.colorbar()
        self.m.drawcoastlines()
        self.m.drawparallels(range(-80,81,20), labels=[1,0,0,0])
        self.m.drawmeridians(range(-180,180,60), labels=[0,0,0,1])
        return my_colorbar
