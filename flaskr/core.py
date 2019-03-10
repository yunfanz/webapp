import functools, os, sys
import numpy as np
import tensorflow as tf
import tempfile
from PIL import Image
import matplotlib.pyplot as plt
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_from_directory, jsonify
)
from werkzeug.utils import secure_filename

DATA_FOLDER = 'data'
TMP_FOLDER = 'tmp'
STATIC_FOLDER = os.path.join('flaskr', 'static')
ALLOWED_EXTENSIONS = set(['npy', 'npz'])

KEYS_PATH = os.path.join(DATA_FOLDER, 'keys.npy')
MODEL_PATH = os.path.join(DATA_FOLDER, 'frozen_model.pb')

bp = Blueprint('core', __name__, url_prefix='/')

# load data
keys = np.load(KEYS_PATH)

def load_graph(frozen_graph_filename):
   """ Function to load frozen TensorFlow graph"""
   with tf.gfile.GFile(frozen_graph_filename, "rb") as f:
       graph_def = tf.GraphDef()
       graph_def.ParseFromString(f.read())
   with tf.Graph().as_default() as graph:
       tf.import_graph_def(graph_def, name="prefix")
   return graph

def _plot_image(target_path, img):
    f, ax = plt.subplot(figsize=(12,8))
    ax.imshow(img.squeeze(), aspect='auto')
    plt.tight_layout()
    plt.savefig(target_path)
    return 

graph = load_graph(MODEL_PATH)
x = graph.get_tensor_by_name('prefix/input_:0')
y = graph.get_tensor_by_name('prefix/enc_norm:0')
sess = tf.Session(graph=graph)

num_dims = keys.shape[1]

def allowed_file(filename):
    # returns true if file's extension is supported
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=('GET', 'POST'))
def home():
    return render_template('core/home.html', wat_image=request.args.get('wat_image'))
    
@bp.route('/image/<path:filename>', methods=('GET',))
def serve_image(filename):
    print(filename, file=sys.stderr)
    return send_from_directory('../tmp/', filename)

@bp.route('/query', methods=('POST',))
def query_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Please select a file')
            return redirect(url_for('core.home'))
        file = request.files['file']
        if file.filename == '':
            flash('Please select a file')
            return redirect(url_for('core.home'))
        if file and allowed_file(file.filename):
            # save the file
            filename = os.path.join(TMP_FOLDER, 'f' + next(tempfile._get_candidate_names()))
            file.save(filename)

            #try:
            im = np.load(filename).astype(np.float32)
            im *= (1.0/im.max())

            # check image size
            if im.shape != (16, 128):
                flash('Image must be 16x128')
                return redirect(url_for('core.home'))
            im = im.reshape((1, 16, 128, 1))

            # run tensorflow inference
            _, vec = sess.run([x, y], feed_dict={x: im})
            
            # compare with keys
            sim = keys @ vec.reshape((32,))
            idx = np.argmax(sim)
            flash(str(idx))
            
            im_ = np.ones_like(im)
            wat_path = 'i' + next(tempfile._get_candidate_names()) + '.png'
            _plot_image(wat_path, np.vstack([im, im_]))
            

            #out_im = Image.fromarray(np.ones((100,100), dtype=np.uint8) * idx * 2)
            #out_im.save(os.path.join(TMP_FOLDER, wat_path))
            
            obj = {
                'idx': int(idx),
                'dist': float(sim[idx]),
                'wat_path': '/image/' + wat_path
            }
            
            os.remove(filename)
            
            return jsonify(obj)
