import ast
import os
import matplotlib.pyplot as plt
from typing import Any, Callable, Literal


def is_float(element: Any) -> bool:
    try:
        float(element)
        return True
    except ValueError:
        return False


def plot_df(df, ykey, fpath, xkey='time',
            xlabel="", ylabel="",
            yscale: Literal['linear', 'log', 'symlog', 'logit'] = 'linear',
            title="",
            ylim=(None, None)):
    fig, ax = plt.subplots()
    ax.plot(df[xkey], df[ykey])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_yscale(yscale)
    ax.set_title(title)
    ax.set_ylim(ylim)
    ax.grid()
    fig.tight_layout()
    fig.savefig(fpath)
    plt.close(fig)
    # return fig, ax


def parse_literal(element: str):
    """Converts string to literal if possible, else returns the string

    Examples
    --------
    >>> parse_literal("1.0")
    1.0
    >>> parse_literal("1")
    1
    >>> type(parse_literal("1"))
    <class 'int'>
    >>> type(parse_literal("1.0"))
    <class 'float'>
    """

    try:
        return ast.literal_eval(element)
    except ValueError:
        return element

def parse_tag(tag):
    ret = {}
    """
    [n_flows=1][bw_mbps=100][delay_ms=50][queue_size_bdp=1][cca=vegas]
    """
    for kv in tag.split(']['):
        kv = kv.replace('[', '').replace(']', '')
        key, value = kv.split('=')
        ret[key] = parse_literal(value)
    return ret


def try_except(function: Callable):
    try:
        return function()
    except Exception:
        import sys
        import traceback

        import ipdb
        extype, value, tb = sys.exc_info()
        traceback.print_exc()
        ipdb.post_mortem(tb)


def try_except_wrapper(function):
    def func_to_return(*args, **kwargs):
        def func_to_try():
            return function(*args, **kwargs)
        return try_except(func_to_try)
    return func_to_return


def plot_multi_exp(input_dir: str, output_dir: str,
                   ext: str, plot_single_exp: Callable):
    for root, _, files in os.walk(input_dir):
        for filename in files:
            if (filename.endswith(ext)):
                fpath = os.path.join(root, filename)
                # dirpath = fpath.replace(ext, '')
                dirpath = os.path.dirname(fpath)
                rel_path = os.path.relpath(dirpath, input_dir)
                this_out_dir = os.path.join(output_dir, rel_path)
                plot_single_exp(fpath, this_out_dir)
