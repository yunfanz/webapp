import functools, os, sys
import numpy as np
import tensorflow as tf
import tempfile
from PIL import Image
import matplotlib.pyplot as plt
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename

DATA_FOLDER = 'data'
TMP_FOLDER = 'tmp'
SYS_TMP_FOLDER = tempfile.gettempdir()

STATIC_FOLDER = os.path.join('flaskr', 'static')
ALLOWED_EXTENSIONS = set(['npy', 'npz'])

KEYS_PATH = os.path.join(DATA_FOLDER, 'keys.npy')
META_PATH = os.path.join(DATA_FOLDER, 'meta.npy')
MODEL_PATH = os.path.join(DATA_FOLDER, 'frozen_model.pb')

bp = Blueprint('core', __name__, url_prefix='/')

# load data
keys = np.load(KEYS_PATH)
meta = np.load(META_PATH)

def _load_graph(frozen_graph_filename):
   """ Function to load frozen TensorFlow graph"""
   with tf.gfile.GFile(frozen_graph_filename, "rb") as f:
       graph_def = tf.GraphDef()
       graph_def.ParseFromString(f.read())
   with tf.Graph().as_default() as graph:
       tf.import_graph_def(graph_def, name="prefix")
   return graph

def _plot_image(target_path, img):
    f, ax = plt.subplots(figsize=(8,6))
    im = ax.imshow(img.squeeze(), aspect='auto')
    f.colorbar(im)
    plt.tight_layout()
    plt.savefig(target_path)
    return 

def _retrieve_image(meta, data_dir="/datax/theta3_split/"):
    basename = '_'.join(meta[0].split('.'))
    idx = meta[1]
    fields = basename.split('_')
    prefix = '_'.join(fields[:3])
    time_stamp = '_'.join(fields[3:5])
    obstarget = fields[5]
    scan_num = fields[6]
    coarse_chan = fields[9]
    path = data_dir+'/'.join([prefix, obstarget, time_stamp, scan_num, coarse_chan, idx])+'.npy'
    try:
        img_ = np.load(path).squeeze()
    except:
        print("Image path not exist", path)
        img_ = None
    return img_

graph = _load_graph(MODEL_PATH)
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
    return send_from_directory(SYS_TMP_FOLDER, filename)

@bp.route('/query', methods=('POST',))
def query_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'message': 'No file specified'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No file specified'})

        if file and allowed_file(file.filename):
            # save the file
            filename = os.path.join(TMP_FOLDER, 'f' + next(tempfile._get_candidate_names()))
            file.save(filename)

            #try:
            im = np.load(filename).astype(np.float32)
            im *= (1.0/im.max())

            # check image size
            if im.shape != (16, 128):
                print("Unsupported image dimensions received")
                return jsonify({'message': 'unsupported image dimensions. Only 16x128 images allowed.'})
            im = im.reshape((1, 16, 128, 1)).astype(np.float32)

            # run tensorflow inference
            vec = sess.run(y, feed_dict={x: im})
            
            # compare with keys
            sim = keys @ vec.reshape((32,))
            idx = np.argmax(sim)
            
            im_ = _retrieve_image(meta[idx])
            if im_ is None:
                im_ = np.ones_like(im)
            wat_path = 'i' + next(tempfile._get_candidate_names()) + '.png'
            im_ *= (1.0/im_.max())

            _plot_image(os.path.join(SYS_TMP_FOLDER, wat_path), np.vstack([im.squeeze(), im_.squeeze()]))

            #out_im = Image.fromarray(np.ones((100,100), dtype=np.uint8) * idx * 2)
            #out_im.save(os.path.join(TMP_FOLDER, wat_path))
            
            obj = {
                'idx': int(idx),
                'dist': float(sim[idx]),
                'wat_path': '/image/' + wat_path
            }
            
            os.remove(filename)
            return jsonify(obj)
