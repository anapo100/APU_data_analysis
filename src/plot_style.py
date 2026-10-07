import sys
sys.dont_write_bytecode = True
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from plot_preprocessing import style

def apply_style(dpi=160):
    style()
    plt.rcParams['savefig.dpi']=dpi

def save_figure(path, figure):
    figure.savefig(path,bbox_inches='tight',facecolor='white')
    plt.close(figure)
    return path
