import functools, os, sys

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import numpy as np

DATA_DIR = 'data'
UPLOAD_FOLDER = 'uploads'
bp = Blueprint('core', __name__, url_prefix='/')

# load data
keys = np.load(os.path.join(DATA_DIR, 'keys.npy'))

@bp.route('/', methods=('GET', 'POST'))
def home():
    return render_template('core/home.html')

@bp.route('/query', methods=('POST',))
def query_image():
    
    return ''