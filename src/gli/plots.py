"""Plot helpers for GLI simulation results."""


def configure_axes(ax, title: str, xlabel: str, ylabel: str):
    """Apply common labels to a matplotlib axis."""

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    return ax
